import re
import keyring
import telnetlib
import time
from pprint import pprint
from switch_management_refactoring import full_connection, mku_finder, begin_connection, end_connection, snmp_get_next, connector, ip_ping_checker, get_model, check_ip, checkswmgmt, model_choicer
'''Надо переписать шаблоны через yaml
Неправильная последовательность команд. Сначала тегом прокидывает везде, что неправильно. Надо добавить эту команду после генерации ACL'''

def dlink_request(ip,OIDS):
    '''На вход поступает ip адрес и словарь с OID, которые необходимо обработать.
    На выходе словарь с полученными значениями.'''

    try:
        result = {}
        for request_data, request_oid in OIDS.items():
            if request_data == 'HOSTNAME':
                result[request_data] = snmp_get_next(ip,request_oid,standalone_value=True)
            elif request_data == 'UPTIME':
                ticks = (snmp_get_next(ip,request_oid,standalone_value=True)) #timeticks
                seconds = int(ticks)/100
                uptime = timedelta(seconds=seconds)
                result[request_data] = str(uptime)
            else:
                result[request_data] = snmp_get_next(ip,request_oid)
        return result
    except:
        print(ip,request_oid, 'error')

def recur_maker(port,vlan):
    '''Находит первый порт, первый влан.
    На основе этого генерирует список вланов на портах и возвращает его.'''

    if port == 1:
        return [i for i in range(vlan,vlan+28)]
    else:
        return recur_maker(port-1,vlan-1)

def setup_vlan_on_mag_ports(mgmt_vlan, vlan_for_100_plus,tn):
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

    dlink_oids = {
        'PVID': '1.3.6.1.2.1.17.7.1.4.5.1.1'
    }
    pvids = dlink_request(ip,dlink_oids)['PVID']
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
    return array_of_vlans[int(port_for_using)-1]

def acl_20_searcher(tn,model):
    '''Отправляет команду show config current_config include "config access_profile profile_id 20"
    Возвращает список портов в правиле об IPV6'''

    command_for_acl_20 = 'show config current_config include "config access_profile profile_id 20"\r'
    if "DES-1210-28/ME/B2" in model or "DES-1210-28/ME/B3" in model:
        regex_for_acl_20 = r'config\s+access_profile\s+profile_id\s+20\s+add\s+access_id\s+\d+\s+ethernet\s+ethernet_type\s+0x86[dD]*\s+port\s+(?P<ports>\S+)\s+permit'
    else:
        regex_for_acl_20 = r'config\s+access_profile\s+profile_id\s+20\s+add\s+access_id\s+\d\s+ethernet\s+ethernet_type\s+0x86[dD]*\s+port\s+(?P<ports>\S+)\s+permit'
    try:
        tn.write(command_for_acl_20.encode('ascii'))
        response = tn.read_until(b'#', timeout=30).decode('ascii') #30 секунд, потому что на некоторых 1210 очень долго идёт ответ
        ports_20_acl = re.search(regex_for_acl_20,response).group('ports')
        return ports_20_acl
    except:
        #print('ACL 20 not found or timeout error')
        return False

def acl_20_configuring(ports,port):
    '''На вход поступает список портов текстового вида '1,2,3,4,25-28' и номер порта под 100+.
    Возвращает список портов в виде списка  ['1', '2', '3', '4', '5', '6', '7', '8', '25', '26', '27', '28'], исключая порт с 100+'''

    res = []
    if len(ports) <= 2:
        return [ports]
    elif ',' in ports:
        splitted = ports.split(',')
        for each in splitted:
            if '-' in each:
                port_range = each.split('-')
                piece_of_ports = [i for i in range(int(port_range[0]),int(port_range[1])+1)]
                res.extend(piece_of_ports)
            else:
                res.append(int(each))
    else:
        splitted = ports.split('-')
        piece_of_ports = [i for i in range(int(splitted[0]),int(splitted[1])+1)]
        res.extend(piece_of_ports)
    sorted(res)
    res = list(map(str,res))
    res.remove(port)
    return res


def commands_100_plus_constructor(vlans_list, port, vlan_for_100_plus, model, tn, ports_for_acl_20 = None):
    '''Генерирует команды для отправки, возвращает список с командами'''

    regex_for_mgmt = r'(\d99)'
    global mgmt_vlan
    mgmt_vlan = None
    res = []
    if ports_for_acl_20:
        IPV6PORTS = ','.join(ports_for_acl_20)
    for vlan in vlans_list:
        mgmt_vlan = re.match(regex_for_mgmt, vlan)
        if mgmt_vlan:
            mgmt_vlan = mgmt_vlan.group()
            break

    command_for_setup_vlan = setup_vlan_on_mag_ports(mgmt_vlan, vlan_for_100_plus,tn)
    command_for_create_vlan = 'create vlan '+str(vlan_for_100_plus)+' tag '+str(vlan_for_100_plus) +'\r'
    res.append(command_for_create_vlan)
    res.append(command_for_setup_vlan)
    for vlan in vlans_list:
        if vlan == '1':
            res.append('config vlan vl 1 del ' + port + '\r')
        else:
            res.append('config vlan '+vlan+' delete '+ port + '\r')
    if "DES-1210-28/ME/B2" in model or "DES-1210-28/ME/B3" in model:
        with open('templates\\commands_for_1210.txt', 'r') as f:
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
        print('Created file:'+ip+'_100_plus.txt')
        return res
    else:
        with open('templates\\commands_for_d_link.txt', 'r') as f:
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
        print('Created file:'+ip+'_100_plus.txt')
        return res

def commands_maker(ip,port,model,tn):
    '''Исходя из данных, инициализируется подключение, ищет порт.
    Далее конструирует последовательность команд для заливки на коммутатор.'''

    try:
        show_vlans = 'show vlan port '+port+'\r'
        tn.write(show_vlans.encode('ascii'))
        final_read = tn.read_until(b'#', timeout=5).decode('ascii')
        vlans = re.findall(r'^\s+(\d+)', final_read, re.MULTILINE)
        global vlan_for_100_plus
        vlan_for_100_plus = parser(ip,port)
        try:
            ports_for_acl_20 = acl_20_searcher(tn,model)
            ports_ipv6 = acl_20_configuring(ports_for_acl_20,port)
        except:
            print("Can't make ACL 20.")
            ports_ipv6 = None
        commands = commands_100_plus_constructor(vlans, port, vlan_for_100_plus, model, tn, ports_for_acl_20 =ports_ipv6)
        return commands, tn
    except:
        tn.close()
        print('Error during commands_maker()')
        input('Press any key to quit.')
    
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

def commands_for_branch(vlan_for_100_plus,ports):
    '''На вход влан для 100+ и порты, где прописан влан менеджмента. '''
    
    creating_vlan = 'create vlan {} tag {}\r'.format(vlan_for_100_plus,vlan_for_100_plus)
    config_ports = 'config vlan {} add tag {}\r'.format(vlan_for_100_plus, ports)
    return [creating_vlan,config_ports,'save\r']

def mgmt_parser(user, passw, tn, mgmt_vlan):
    '''На вход логин, пароль, телнет объект, влан менеджмента.
    Вводит команду на свиче, возвращает список портов, где прописан влан менеджмента и телнет объект. '''

    regex_for_tagged = r'Tagged\s+Ports\s+:\s+(?<ports>\S+)'
    command = 'show vlan '+mgmt_vlan +'\r'
    tn.write(command.encode('ascii'))
    response = tn.read_until(b'#', timeout=5)
    ports = re.search(regex_for_tagged, response).group('ports')
    return ports, tn

def vlan_100_writer(tn, commands_on_uplink):
    '''На вход телнет объект и список команд, которые нужно прописать на свиче.
    Если всё проходит, возвращает True '''

    for command in commands_on_uplink:
        tn.write(command.encode('ascii'))
        tn.read_until(b'#', timeout=5)
    return True

def neighbors_changer(ips, user, password):
    '''На вход поступает список ip адресов, логин, пароль. 
    Инициализируется подключение, происходит поиск портов, где влан менеджмента.
    Генерируются команды для отправки на свич. 
    Команды отправляются. В случае успеха возвращает True.'''

    for ip in ips:
        if ip_ping_checker(ip):
            tn, data = full_connection(user, password, ip)
            if 'D-Link' in data:
                ports, tn = mgmt_parser(user,password,tn,mgmt_vlan)
                commands = commands_for_branch(vlan_for_100_plus,ports)
                if vlan_100_writer(tn,commands):
                    tn.close()
                    return True

def main(user,passw,ip,port):

    if ip_ping_checker(ip):
        tn, data = full_connection(user, passw, ip) #It's global now!
        if 'D-Link' in data:
            model = data['D-Link']
            print(ip,'модель коммутатора: ', model)
            try:
                commands, tn = commands_maker(ip,port,model,tn)
                end_connection(user, passw, ip, data, tn)
                path = mku_finder(user, passw, ip)
                return path, commands
            except:
                end_connection(user, passw, ip, data, tn)
                tn.close()
                print('Error during main()')
                input('Press any key to quit.')
        else:
            print("It's not D-Link!")
            input('Press any key to quit.')


if __name__ == '__main__': 
    ip = input('Enter ip-address: ').strip() #'192.168.0.1'
    port = input('Enter port:').strip() #'27'
    USER = 'khusainov.if'     #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< CAUTION!!!!
    PASSWORD = keyring.get_password("work_for_switches", "khusainov.if")   #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< CAUTION!!!!
    path, commands = main(USER,PASSWORD, ip, port)
    print(vlan_for_100_plus)
    neighbors_changer(path,USER,PASSWORD)
