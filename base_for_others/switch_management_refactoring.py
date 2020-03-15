from pysnmp.entity.rfc3413.oneliner import cmdgen
import re
import keyring
from time import time, localtime, strftime
from datetime import datetime, timedelta
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import os
import json
from ipaddress import ip_address
import socket, re, time
import telnetlib
from collections import deque

def snmp_get_next(ip,OID,community = keyring.get_password("snmp", "khusainov.if"),port = 161,standalone_value=False):
    '''Аналог команды snmpwalk. На вход IP адрес и OID, который надо итерировать.
    Возвращает словарь, где ключ это число следующее за поданным на вход OID, 
    а значение ключа данные хранящиеся в этом OID
    standalone_value отвечает за флаг для того, чтобы получить одно значение в итерации.
    В этом случае возвращает словарь с ip адресом и значением OID'''

    res = {}
    cmdGen = cmdgen.CommandGenerator()
    errorIndication, errorStatus, errorIndex, varBindTable = cmdGen.nextCmd(cmdgen.CommunityData(community),
    cmdgen.UdpTransportTarget((ip, 161)),OID)
    if errorIndication:
        print(errorIndication)
    else:
        if errorStatus:
            print('%s at %s' % (errorStatus.prettyPrint(),errorIndex and varBindTable[-1][int(errorIndex)-1] or '?'))
        else:
            for varBindTableRow in varBindTable:
                for name, val in varBindTableRow:
                    if standalone_value:
                        return val.prettyPrint()
                        #res[ip] = val.prettyPrint()
                    else:
                        res[(re.search(r'(\d+$)', name.prettyPrint()).group())] = val.prettyPrint()
                    #print('%s = %s' % (name.prettyPrint(), val.prettyPrint()))
    return res

def check_ip(ip):
    '''Проверка соответствия IP-адреса формату X.X.X.X, где 0<=Х<=255'''

    try:
        ip_address(ip)
    except ValueError:
        return False
    else:
        return True
  
def checkswmgmt(ip,timeout=10):
    '''На вход нужно подавать IP-адрес, 
    функция проверит сокет 23 порта и выдаст ответ - открыт сокет или нет.'''

    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((ip,23))
        sock.close()
        return True
    except:
        return False

def ip_ping_checker(ip):
    '''Проверка ip на соответствие, проверка сокета на доступность.'''

    try:
        if check_ip(ip):
            if checkswmgmt(ip):
                return True
            else:
                print(ip, 'недоступен.')
                return False
        else:
            print(ip, 'не соответствует формату.')
            return False
    except:
        return False

def get_model(ip):
    '''Функция делает SNMP запрос по стандартному OID модели и выдаёт ответ. 
    Эквивалент snmpwalk -v 2c -c SNMPCOMMUNITY 192.168.0.1 1.3.6.1.2.1.1.1'''

    OID = '1.3.6.1.2.1.1.1'
    res = (snmp_get_next(ip,OID,standalone_value=True))
    if res:
        return res
    else:
        print('OID or snmp_get_next error.')

def model_choicer(model):
    '''Принимает на вход ответ snmp-запроса о модели.
    На выходе даёт словарь, где ключ производитель, а значение модель соответствующее модели.'''

    models = {}
    if model == "DES-1210-28/ME/B2":
        models['D-Link'] = 'DES-1210-28/ME/B2'
        return models
    elif model == "DES-1210-28/ME/B3":
        models['D-Link'] = 'DES-1210-28/ME/B3'
        return models
    elif model == "DES-3200-26/C1 Fast Ethernet Switch":
        models['D-Link'] = 'DES-3200-26/C1'
        return models
    elif model == "D-Link DES-1228/ME Metro Ethernet Switch":
        models['D-Link'] = 'DES-1228/ME'
        return models
    elif model == "D-Link DES-3028 Fast Ethernet Switch":
        models['D-Link'] = 'DES-3028'
        return models
    elif model == "D-Link DES-3200-28 Fast Ethernet Switch":
        models['D-Link'] = 'DES-3200-28'
        return models
    elif 'S2320-28TP-EI-AC' in model:
        models['Huawei'] = 'S2320-28TP-EI-AC'
        return models
    elif 'S2350-28TP-EI-AC' in model:
        models['Huawei'] = 'S2350-28TP-EI-AC'
        return models
    elif 'S5320-28P-LI-AC' in model: #может быть и с лицензией и без, нужно добавить проверку
        models['Huawei'] = 'S5320-28P-LI-AC'
        return models
    elif 'S5320-28P-LI-AC' in model:
        models['Huawei'] = 'S5320-28P-LI-AC'
        return models
    elif 'S5320-28TP-LI-AC' in model:
        models['Huawei'] = 'S5320-28TP-LI-AC'
        return models
    elif model == 'MyPower S3100-9TP':
        models['Maipu'] = 'S3100-9TP'
        return models
    elif model == 'JetStream 24-Port Gigabit L2 Managed Switch with 4 SFP Slots and DC Power Supply':
        models['Tp-Link'] = 'T2600G-28TS_DC'
        return models
    elif model == 'JetStream 24-Port Gigabit L2+ Managed Switch with 4 SFP Slots':
        models['Tp-Link'] = 'T2600G-28TS_AC'
        return models
    elif model == 'MES2428 DC 28-port 1G Managed Switch':
        models['Eltex'] = 'MES2428'
        return models
    else:
        print('Описания действий для '+model+' нет в скрипте.')
        return None

def connector(user,passw,host,model):
    '''Принимает на вход логин, пароль, адрес подключения, словарь с данными, где ключ производитель, значение модель.
    Подключается, авторизуется и возвращает объект, содержащий текущее соединение.'''

    if 'D-Link' in model:
        return d_link_connect(user,passw,host)
    elif 'Huawei' in model:
        return huawei_connect(user,passw,host)
    elif 'Tp-Link' in model:
        return tp_link_connect(user,passw,host)
    elif 'Maipu' in model:
        pass
    elif 'Eltex' in model:
        return eltex_connect(user,passw,host)
    else:
        print('В скрипте нет модели',model)
        return None

def d_link_connect(user,passw,host):
    '''Инициализирует подключение к d-link, возвращает объект с соединением'''

    telnetconnect = telnetlib.Telnet()
    telnetconnect.open(host, 23, 5)
    telnetconnect.read_until(b'name:', timeout=3)
    telnetconnect.write(user.encode('ascii') + b'\n')
    telnetconnect.read_until(b'word:', timeout=3)
    telnetconnect.write(passw.encode('ascii') + b'\r')
    login_mes = telnetconnect.read_until(b'#', timeout=5)
    if b'#' in login_mes:
        print(host,'login ok!')
        return telnetconnect
    else:
        print("Can't login.")
    
def eltex_connect(user,passw,host):
    '''Инициализирует подключение к eltex, возвращает объект с соединением'''

    telnetconnect = telnetlib.Telnet()
    telnetconnect.open(host, 23, 5)
    telnetconnect.read_until(b'login:', timeout=3)
    telnetconnect.write(user.encode('ascii') + b'\n')
    telnetconnect.read_until(b'word:', timeout=3)
    telnetconnect.write(passw.encode('ascii') + b'\r')
    login_mes = telnetconnect.read_until(b'#', timeout=5)
    if b'#' in login_mes:
        print(host,'login ok!')
        return telnetconnect
    else:
        print("Can't login.")

def huawei_connect(user,passw,host):
    '''Инициализирует подключение к huawei, возвращает объект с соединением'''

    telnetconnect = telnetlib.Telnet()
    telnetconnect.open(host, 23, 5)
    telnetconnect.read_until(b'name:', timeout=3)
    telnetconnect.write(user.encode('ascii') + b'\n')
    telnetconnect.read_until(b'word:', timeout=3)
    telnetconnect.write(passw.encode('ascii') + b'\r')
    try:
        login_mes = telnetconnect.read_until(b'>', timeout=5)
        if b'>' in login_mes:
            print('Login ok!')
            return telnetconnect
        else:
            print("Can't login.")
    except:
        print("Can't find")

def tp_link_connect(user,passw,host):
    '''Инициализирует подключение к tp-link, возвращает объект с соединением'''

    telnetconnect = telnetlib.Telnet()
    telnetconnect.open(host, 23, 5)
    telnetconnect.read_until(b'ser:', timeout=3)
    telnetconnect.write(user.encode('ascii') + b'\r')
    telnetconnect.read_until(b'word:', timeout=3)
    telnetconnect.write(passw.encode('ascii') + b'\r')
    login_mes = telnetconnect.read_until(b'>', timeout=5)
    login_mes
    if b'>' in login_mes:
        print('Login ok!')
        return telnetconnect
    else:
        print("Can't login.")


def begin_connection(user,passw,host,model,tn):
    '''Вступительные команды после подключения к коммутатору.'''

    def d_link_begin(user,passw,host):
        commands_for_d_link = [
            'enable admin\r',
            '\r',
            'disable clipaging\r']
        try:
            for command in commands_for_d_link:
                tn.write(command.encode('ascii'))
                tn.read_until(b'#', timeout=5)
            print('Connection opened.')
        except:
            print('Error during d_link_begin()')

    def tp_link_begin(user,passw,host):
        commands_for_tp_link = [
            'configure\r',
            'no clipaging\r',
            'exit\r']
        try:
            tn.write(b'enable\r')
            tn.read_until(b'>', timeout=5)
            for command in commands_for_tp_link:
                tn.write(command.encode('ascii'))
                tn.read_until(b'#', timeout=5)
            print('Connection opened.')
        except:
            print('Error during tp_link_begin()')

    def huawei_begin(user,passw,host):
        commands_for_huawei = [
            'screen-length 0 temporary\r']
        try:
            for command in commands_for_huawei:
                tn.write(command.encode('ascii'))
                tn.read_until(b'>', timeout=5)
            print('Connection opened.')
        except:
            print('Error during huawei_begin()')
    
    def eltex_begin(user,passw,host):
        commands_for_eltex = ['set cli pagination off\r']
        for command in commands_for_eltex:
            tn.write(command.encode('ascii'))
            tn.read_until(b'#', timeout=5)
        print('Connection opened.')

    try:
        if 'D-Link' in model:
            d_link_begin(user,passw,host)
        elif 'Huawei' in model:
            huawei_begin(user,passw,host)
        elif 'Tp-Link' in model:
            tp_link_begin(user,passw,host)
        elif 'Maipu' in model:
            eltex_begin(user,passw,host)
        elif 'Eltex' in model:
            eltex_begin(user,passw,host)
        else:
            print('В скрипте нет модели',model)
            return None
    except:
        print('Begin_connection() error.')

def end_connection(user,passw,host,model,tn):
    '''Заключительные команды после подключения к коммутатору.'''

    def d_link_end(user,passw,host):
        commands_for_d_link = [
        'enable clipaging\r',
        'logout\r']
        try:
            for command in commands_for_d_link:
                tn.write(command.encode('ascii'))
                tn.read_until(b'#', timeout=5)
            tn.close()
            print('Connection closed.')
        except:
            print('Error during d_link_end()')

    def tp_link_end(user,passw,host):
        commands_for_tp_link = [
            'configure\r',
            'clipaging\r',
            'exit\r'
            'copy r s\r'
            'logout\r']
        try:
            for command in commands_for_tp_link:
                tn.write(command.encode('ascii'))
                tn.read_until(b'#', timeout=5)
            tn.close()
            print('Connection closed.')
        except:
            print('Error during tp_link_end()')

    def huawei_end(user,passw,host):
        commands_for_huawei = [
            'quit\r']
        try:
            for command in commands_for_huawei:
                tn.write(command.encode('ascii'))
                tn.read_until(b'VTY users on line is 0.', timeout=5)
            tn.close()
            print('Connection closed.')
        except:
            print('Error during huawei_end()')
    
    def eltex_end(user,passw,host):
        commands_for_eltex = ['end\r','set cli pagination on\r',
            'logout\r']
        #try:
        for command in commands_for_eltex:
            tn.write(command.encode('ascii'))
        print('Connection closed.')
        #except:
        #    print('Error during eltex_end()')

    try:
        if 'D-Link' in model:
            d_link_end(user,passw,host)
        elif 'Huawei' in model:
            huawei_end(user,passw,host)
        elif 'Tp-Link' in model:
            tp_link_end(user,passw,host)
        elif 'Maipu' in model:
            pass
        elif 'Eltex' in model:
            eltex_end(user,passw,host)
        else:
            print('В скрипте нет модели',model)
            return None
    except:
        print('End_connection() error.')

def lldp_request(user,passw,host,model,tn):

    result = {}
    res = {}
    if 'D-Link' in model:
        port_lldp = [b'show lldp rem 25\r',b'show lldp rem 26\r',b'show lldp rem 27\r',b'show lldp rem 28\r']
        for port_lldp_command in port_lldp:
            tn.write(port_lldp_command)
            response = tn.read_until(b'#', timeout=5).decode('ascii','ignore')
            if not "Remote Entities Count : 0" in response:
                try:
                    res[re.search(r'Port ID : (?P<port>\d+)',response).group('port')] = response
                except AttributeError:
                    print('NoneType. LLDP request fail!')
                    return None
        result[host] = res
        with open(ip+'.json', 'w') as f:
            json.dump(result, f, sort_keys=True, indent=2)
        return result
                

    elif 'Huawei' in model:
        tn.write(b'display lldp ne\r')
        res = tn.read_until(b'>', timeout=5).decode('ascii')
        with open (ip+'.txt', 'w') as f:
            f.write(res)
        return res

    elif 'Tp-Link' in model:
        tn.write(b'show lldp ne int\r')
        res = tn.read_until(b'#', timeout=5).decode('ascii')
        with open (ip+'.txt', 'w') as f:
            f.write(res)
        return res

    elif model['Maipu']:
        return None
    else:
        print('В скрипте нет модели',model)
        return None

def mku_checker(lldp_response):
    '''На вход поступает вывод команды sh lldp neighboors. Ищет в нём mku. 
    Если нашёл, возвращает True.'''

    if 'D-Link DGS' in lldp_response:
        return True
    else:
        return False

def lldp_parser(lldp_response):
    '''На вход поступает вывод команды show lldp neighboors.
    делает проверку на предмет присутствия DGS.
    При неудаче, ищет ip адреса соседей и возвращает их в виде списка.'''

    ip_of_neighbors = []
    for ip, lldp_res in lldp_response.items():
        for port, lldp_res_full in lldp_res.items():
            if mku_checker(lldp_res_full):
                return ip
            else:
                try:
                    neighbor = re.search(r'((?:\d+\.){3}\d+)', lldp_res_full).group()
                    ip_of_neighbors.append(neighbor)
                except:
                    print("Не удалось найти соседей при парсинге ответа show lldp neighbors на",port, "порте.")
    if ip_of_neighbors:
        #print('Source:',ip, 'Neighbors:', ip_of_neighbors)
        return ip_of_neighbors

def mku_finder(user,passw,host):
    '''Принимает на вход логин, пароль, адрес от которого нужно найти МКУ.
    ВНИМАНИЕ: ИЩЕТ ТОЛЬКО В ПУТИ ПО Д-ЛИНК.
    Возвращает список адресов до МКУ, включая поданный на вход ip.'''

    try:
        tn, model = full_connection(user,passw,host)
    except TypeError:
        pass
    if not 'D-Link' in model:
        print('Passing', host)
        end_connection(user,passw,host,model,tn)
        return False
    
    searched = []
    path_to_dgs = []
    lldp_out = lldp_parser(lldp_request(user,passw,host,model,tn))
    if type(lldp_out) is str:
        print('DGS here:', host)
        path_to_dgs.append(host)
        end_connection(user,passw,host,model,tn)
        return path_to_dgs
    elif lldp_out == None:
        print('Passing', host)
        end_connection(user,passw,host,model,tn)
        return False
    else:
        graph = {host:lldp_out}
        path_to_dgs.append(host)
        searched.append(host)
        search_queue = deque()
        search_queue += graph[host]
        while search_queue:
            current_switch = search_queue.popleft()
            if not current_switch in searched:
                tn, model = full_connection(user,passw, current_switch)
                lldp_out = lldp_parser(lldp_request(user,passw,current_switch,model,tn))
                end_connection(user,passw, current_switch, model, tn)
                if type(lldp_out) is str:
                    print('DGS here:', current_switch)
                    path_to_dgs.append(current_switch)
                    return path_to_dgs
                else:
                    graph.update({current_switch:lldp_out})
                    search_queue += graph[current_switch]
                    searched.append(current_switch)
        print("Can't find path to MKU from", host+".")
        return False
        
def full_connection(user,passw,host):
    '''Принимает на вход логин, пароль, ip.
    Проверяет ip на соответствие формату ip-адресов, доступность.
    Делает запрос по snmp, на основании этого выбирает модель, с которой предстоит работать.
    Далее инициализирует телнет соединение, логнится. 
    Возвращает объект соединения.'''

    data = {}
    model_snmp_res = get_model(host)
    try:
        data.update(model_choicer(model_snmp_res))
        print(data)
        print(host,'а модель такая: ', model_choicer(model_snmp_res))
        try:
            tn = connector(user,passw,host, data)
            begin_connection(user,passw,host, data, tn)
            return tn, data
        except Exception as error:
            print("Can't connect or can't login,", 'traceback:\n', error)
            return False
    except:
        print('No such model in model_choicer().')
        return False

def main(ip):
    
    USER = 'khusainov.if'     #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< CAUTION!!!!
    PASSWORD = keyring.get_password("work_for_switches", "khusainov.if")   #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< CAUTION!!!!
    #tn, data = full_connection(USER, PASSWORD, ip)
    if ip_ping_checker(ip):
        path = mku_finder(USER, PASSWORD, ip)
    #end_connection(USER, PASSWORD, ip, data, tn)
    #tn.close()
        print(path)

if __name__ == '__main__':
    ips = []
    with open('ips.txt', 'r') as f:
        for ip in f:
            ip = ip.strip()
            ips.append(ip)
    for ip in ips:
        main(ip)