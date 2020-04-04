import re
import pyperclip
import win32clipboard
import keyring
import telnetlib
import time
from pprint import pprint
from switch_management import begin_connection, end_connection, snmp_get_next, connector, ip_ping_checker, get_model, check_ip, checkswmgmt, model_choicer

'''Надо переписать шаблоны через yaml'''

def dlink_request(ip,OID):
    '''На вход поступает ip адрес и OID.
    На выходе значение за этим OID.'''

    try:
        result = snmp_get_next(ip,OID)
        return result
    except Exception as error:
        print('dlink_request() error:', error)

def recur_maker(port,vlan):
    '''Находит первый порт, первый влан.
    На основе этого генерирует список вланов на портах и возвращает его.'''

    if port == 1:
        return [i for i in range(vlan,vlan+28)]
    else:
        return recur_maker(port-1,vlan-1)

def setup_vlan_on_mag_ports(mgmt_vlan, vlan_for_100_plus):
    '''Генерирует команды для прокидывания влана на тех портах, где присутствует влан менеджмента.'''

    command = 'show vlan ' + mgmt_vlan + '\r'
    tn.write(command.encode('ascii'))
    output = tn.read_until(b'#', timeout=5).decode('ascii')
    tagged_mgmt_vlan = re.findall(r'Tagged\s*Ports\s*\:\s*(\S+)', output)
    if tagged_mgmt_vlan:
        tagged_mgmt_vlan = tagged_mgmt_vlan[0]
        return 'config vlan ' + str(vlan_for_100_plus) + ' add ' + ' tagged ' + str(tagged_mgmt_vlan) + '\r'

def parser(ip, port_for_using):
    '''Проверяет pvid по snmp и помещает все вланы в список. 
    Возвращает влан, который нужно использовать для 100+ на порте'''

    dlink_pvid = '1.3.6.1.2.1.17.7.1.4.5.1.1'
    pvids = dlink_request(ip,dlink_pvid)
    pppoe_vlans = [i for i in range(1000,1500)]
    regex = r'(\d{4})'
    fetch = None
    while not fetch:
        for port, vlan in pvids.items():
            fetch = re.match(regex, vlan)
            if fetch:
                if int(fetch.group()) in pppoe_vlans:
                    fetched_vlan = int(fetch.group())
                    fetched_port = int(port)
                    break
    array_of_vlans = recur_maker(fetched_port,fetched_vlan)
    if array_of_vlans:
        return array_of_vlans[int(port_for_using)-1]
    else:
        return False    

def commands_writer(list_of_commands):
    '''Принимает на вход список команд, отправляет их по очереди'''

    try:
        for command in list_of_commands:
            tn.write(command.encode('ascii'))
            tn.read_until(b'#', timeout=5)
        return True
    except:
        print(command, 'is broken.')
        return False

def acl_20_searcher(tn,model):
    '''Отправляет команду show config current_config include "config access_profile profile_id 20"
    Возвращает список портов в правиле об IPV6'''

    #command_for_acl_20 = 'show config current_config include "config access_profile profile_id 20"\r'
    if "DES-1210-28/ME/B2" in model or "DES-1210-28/ME/B3" in model:
        command_for_acl_20 = 'show config current_config include "0x86dd"\r'
        regex_for_acl_20 = r'config\s+access_profile\s+profile_id\s+20\s+add\s+access_id\s+\d+\s+ethernet\s+ethernet_type\s+0x86[dD]*\s+port\s+(\S+)\s+permit'
    else:
        command_for_acl_20 = 'show config current_config include "0x86DD"\r'
        regex_for_acl_20 = r'config\s+access_profile\s+profile_id\s+20\s+add\s+access_id\s+\d\s+ethernet\s+ethernet_type\s+0x86[dD]*\s+port\s+(\S+)\s+permit'
    try:
        tn.write(command_for_acl_20.encode('ascii'))
        response = tn.read_until(b'#', timeout=30).decode('ascii') #30 секунд, потому что на некоторых 1210 очень долго идёт ответ
        ports_20_acl = re.findall(regex_for_acl_20,response)
        if len(ports_20_acl) == 1:
            return ports_20_acl[0]
        else:
            ports_for_20_acl = ','.join(ports_20_acl)
            return ports_for_20_acl
    except Exception as error:
        print('acl_20_seracher() error is:', error)
        return False

def acl_20_configuring(ports,port_for_100):
    '''На вход поступает список портов текстового вида '1,2,3,4,25-28' и номер порта под 100+.
    Возвращает список портов в виде списка  ['1', '2', '3', '4', '5', '6', '7', '8', '25', '26', '27', '28'], исключая порт с 100+'''

    res = []
    if len(ports) <= 2:
        return [ports]
    elif ',' in ports:
        splitted = ports.split(',')
        for port in splitted:
            if '-' in port:
                port_range = port.split('-')
                piece_of_ports = [i for i in range(int(port_range[0]),int(port_range[1])+1)]
                res.extend(piece_of_ports)
            else:
                res.append(int(port))
    else:
        splitted = ports.split('-')
        piece_of_ports = [i for i in range(int(splitted[0]),int(splitted[1])+1)]
        res.extend(piece_of_ports)
    res = list(map(str,res))
    res.remove(str(port_for_100))
    return res


def commands_100_plus_constructor(vlans_list, port, vlan_for_100_plus, model, ports_for_acl_20 = None):
    '''Генерирует команды для отправки, возвращает список с командами'''

    regex_for_mgmt = r'(\d99)'
    mgmt_vlan = None
    res = []
    if ports_for_acl_20:
        IPV6PORTS = ','.join(ports_for_acl_20)
    for vlan in vlans_list:
        mgmt_vlan = re.match(regex_for_mgmt, vlan)
        if mgmt_vlan:
            mgmt_vlan = mgmt_vlan.group()
            break

    command_for_setup_vlan = setup_vlan_on_mag_ports(mgmt_vlan, vlan_for_100_plus)
    command_for_create_vlan = 'create vlan '+str(vlan_for_100_plus)+' tag '+str(vlan_for_100_plus) +'\r'
    res.append(command_for_create_vlan)
    res.append(command_for_setup_vlan)
    for vlan in vlans_list:
        if vlan == '1':
            res.append('config vlan vl 1 del ' + port + '\r')
        else:
            res.append('config vlan '+vlan+' delete '+ port + '\r')
    if "DES-1210-28/ME/B2" in model or "DES-1210-28/ME/B3" in model:
        commands_maker('templates\\commands_for_1210.txt',ip,IPV6PORTS,res)
    else:
        commands_maker('templates\\commands_for_d_link.txt',ip,IPV6PORTS,res)

def commands_maker(filename,ip,IPV6PORTS,res):
    """Принимает на вход имя шаблона
    Заменяет в нём все нужное, копирует результат в буфер обмена и сохраняет в отдельном файле."""

    with open(filename, 'r') as f:
        command_as_string = f.read()
        command_list = command_as_string.split('\n')
    for command in command_list:
        command=command.replace('PORT', port)
        command=command.replace('VLAN', str(vlan_for_100_plus))
        if ports_for_acl_20:
            command=command.replace('IPV6',IPV6PORTS)
        command=command+'\r'
        res.append(command)
    with open(ip +'_100_plus.txt', 'w') as f:
        for line in res:
            f.write(line.strip('\r'))
            f.write('\n')
    with open(ip +'_100_plus.txt', 'r') as f:
        text = f.read()
        pyperclip.copy(text)
    print('Created file:'+ip+'_100_plus.txt')
    return res

if __name__ == '__main__':
    ip = input('Enter ip-address: ').strip() #'192.168.0.1'
    port = input('Enter port:').strip() #'27'
    USER = 'khusainov.if'     #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< CAUTION!!!!
    PASSWORD = keyring.get_password("work_for_switches", "khusainov.if")   #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< CAUTION!!!!
    data = {}

    if ip_ping_checker(ip):
        model_snmp_res = get_model(ip)
        try:
            data.update(model_choicer(model_snmp_res))
        except TypeError:
            print('Script works only with D-link')
        if 'D-Link' in data:
            model = data['D-Link']
            print(ip,'модель коммутатора: ', model)
            try:
                tn = connector(USER, PASSWORD, ip, data) #It's global now!
                begin_connection(USER, PASSWORD, ip, data, tn)
                show_vlans = 'show vlan port '+port+'\r'
                tn.write(show_vlans.encode('ascii'))
                final_read = tn.read_until(b'#', timeout=5).decode('ascii')
                vlans = re.findall(r'^\s+(\d+)', final_read, re.MULTILINE)
                if len(vlans)>5:
                    vlan_for_100_plus = parser(ip,port)
                    if vlan_for_100_plus:
                        try:
                            ports_for_acl_20 = acl_20_searcher(tn,model)
                            ports_ipv6 = acl_20_configuring(ports_for_acl_20,port)
                            ports_ipv6 = set(ports_ipv6)
                        except Exception as error:
                            print("Can't make ACL 20:", error)
                            ports_ipv6 = None
                        commands_100_plus_constructor(vlans, port, vlan_for_100_plus, model, ports_for_acl_20 =ports_ipv6)
                        end_connection(USER, PASSWORD, ip, data, tn)
                        tn.close()
                        print('Done.')
                        input('Press any key to quit.')
                    else:
                        print(ip,'in this switch no vlan in range 1000-1500.')
                        end_connection(USER, PASSWORD, ip, data, tn)
                        tn.close()
                else:
                    print(port, 'number of vlans in this port <5. Seems like port already 100+ or something.')
                    end_connection(USER, PASSWORD, ip, data, tn)
                    tn.close()
            except Exception as error:
                end_connection(USER, PASSWORD, ip, data, tn)
                tn.close()
                print('Error during main():', error)
                input('Press any key to quit.')
        else:
            print("It's not D-Link!")
            input('Press any key to quit.') 