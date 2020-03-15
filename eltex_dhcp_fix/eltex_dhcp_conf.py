from base_for_others.switch_management_refactoring import *
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool

def send_global_dhcp_command(tn):
    '''Генерирует и отправляет глобальные команды на eltex.'''
    global_commands = [
        'end\r',
        'conf t\r',
        'dcs information option enable\r',
        'dcs information option dhcp enable\r',
        'dcs agent-circuit-id user-defined %i\r',
        'dcs agent-circuit-id suboption-type dhcpv4 user-defined binary\r',
        'dcs remote-agent-id user-defined %M\r',
        'dcs remote-agent-id suboption-type dhcpv4 user-defined binary\r',
        'dcs information option dhcpv6 disable\r',
        'mac access-list extended 3\r',
        ' deny any any encaptype 0x86DD priority 3\r',
        'end\r']
    #with open('global_commands.txt', 'w') as f:
    #    f.write(''.join(global_commands))
    for command in global_commands:
        tn.write(command.encode('ascii'))
        tn.read_until(b'#', timeout=15)
    return tn

def operations_with_set(set1,set2):
    diff1 = set2-set1
    commands = []
    for each in diff1:
        commands.append(f'vlan {each}\r')
        commands.append('no ip dhcp snooping\r')
    diff2=set1-set2
    for each in diff2:
        commands.append(f'vlan {each}\r')
        commands.append('ip dhcp snooping\r')
    return commands

def cancel_vlan_dhcp_commands(tn,pvids_for_check):
    '''Проверяет настройки снупинга и удаляет их, если не соответствуют запросу snmp. '''
    
    tn.write(b'show ip dhcp snooping | grep VLAN\r')
    tn.write(b'\r')
    response = tn.read_until(b'#', timeout=5).decode('ascii','ignore')
    regex_for_get_dhcp_vlan_snoop = r'VLAN\s+:\s+(\d+)'
    vlans = re.findall(regex_for_get_dhcp_vlan_snoop,response)
    if vlans == pvids_for_check:
        return tn
    else:
        vlans = set(sorted(list(map(int,vlans))))
        pvids_for_check = set(sorted(list(map(int,pvids_for_check))))
        commands_for_del_and_add = operations_with_set(pvids_for_check,vlans)
        commands = ['end\r','conf t\r']
        commands.extend(commands_for_del_and_add)
        #with open('commands.txt', 'w') as f:
        #    f.write(''.join(commands))
        for command in commands:
            tn.write(command.encode('ascii'))
            tn.read_until(b'#', timeout=15)
    return tn

def set_vlan_dhcp_snooping_commands(tn,vlans): #dont use
    '''Генерирует и отправляет верные настройки dhcp снупинга на вланы.'''

    global_commands = ['end\r','conf t\r']
    for command in global_commands:
        tn.write(command.encode('ascii'))
        tn.read_until(b'#', timeout=15)
    for vlan in vlans:
        if int(vlan) in range(1000,1500):
            commands = [f'vlan {vlan}\r','ip dhcp snooping\r']
            with open('vlan_commands.txt', 'a') as f:
                f.write(''.join(commands))
            for command in commands:
                tn.write(command.encode('ascii'))
                tn.read_until(b'#', timeout=15)
    tn.write(b'end\r')
    return tn

def set_acl_on_access_port(tn,pvid):
    '''Закидывает acl-ку на аксесс порты'''

    global_commands = ['end\r','conf t\r']
    for command in global_commands:
        tn.write(command.encode('ascii'))
        tn.read_until(b'#', timeout=15)
    for port,vlan in pvid.items():
        if int(vlan) in range(1000,1500):
            commands = [f'interface gigabitethernet 0/{port}\r','mac access-group 3 in\r','exit\r']
            global_commands.extend(commands)
    for command in global_commands:
        tn.write(command.encode('ascii'))
        tn.read_until(b'#', timeout=15)
    #with open('acl_on_acc_ports.txt', 'w') as f:
    #    f.write(''.join(global_commands))
    return tn

def main(ip):
    ''' Основной ход программы '''

    USER = 'khusainov.if'     #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< CAUTION!!!!
    PASSWORD = keyring.get_password("work_for_switches", "khusainov.if")   #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< CAUTION!!!!

    with open('log.txt', 'a') as log:
        if ip_ping_checker(ip):
            try:
                pvid = snmp_get_next(ip,'1.3.6.1.2.1.17.7.1.4.5.1.1')
                pvids = list(pvid.values())[0:24]
                tn, data = full_connection(USER, PASSWORD, ip)
                tn = cancel_vlan_dhcp_commands(tn,pvids)
                tn = send_global_dhcp_command(tn)
                tn = set_acl_on_access_port(tn,pvid)
                try:
                    tn.write(b'end\r')
                    tn.write(b'copy r s\r')
                    tn.read_until(b'#', timeout=30)
                except Exception as error:
                    print("Can't save, traceback:\n",error)
            except Exception as err:
                log.write(ip, err)
            finally:
                end_connection(USER,PASSWORD,ip,data,tn)
                log.write(ip+ ',done\n')

def filename_splitter(rows=100):
    '''На вход подаётся файл с большим количеством строк. 
    При каждом вызове по умолчанию выдаёт 100 следующих строк.'''
    while rows>0:
        rows -=1
        yield rows

def row_splitter(filename):
    '''Функция для генератора. Отдаёт следующую строку если внутри генератора'''
    for row in open(filename, "r"):
        yield row

if __name__ == "__main__":
    USER = 'khusainov.if'     #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< CAUTION!!!!
    PASSWORD = keyring.get_password("work_for_switches", "khusainov.if")   #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< CAUTION!!!!
    ips = []
    gen = (row for row in open('eltex.txt'))
    start = 0
    step = 11
    while start<213:
        ips = []
        if start<step+1:
            for ip in gen:
                ips.append(ip.strip())
                start+=1
                if len(ips) ==10:
                    break
                elif ip ==0:
                    break
        pool = ThreadPool()
        pool.map(main, ips)
        pool.close()
        pool.join()
        step +=step


