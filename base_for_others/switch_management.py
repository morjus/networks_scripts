from pysnmp.entity.rfc3413.oneliner import cmdgen
import re
import keyring
from time import time, localtime, strftime
from datetime import datetime, timedelta
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import os
from ipaddress import ip_address
import socket, re, time
import telnetlib

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
    elif model['Maipu']:
        pass
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
        print('Login ok!')
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
    try:
        if 'D-Link' in model:
            d_link_begin(user,passw,host)
        elif 'Huawei' in model:
            huawei_begin(user,passw,host)
        elif 'Tp-Link' in model:
            tp_link_begin(user,passw,host)
        elif model['Maipu']:
            pass
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

    try:
        if 'D-Link' in model:
            d_link_end(user,passw,host)
        elif 'Huawei' in model:
            huawei_end(user,passw,host)
        elif 'Tp-Link' in model:
            tp_link_end(user,passw,host)
        elif model['Maipu']:
            pass
        else:
            print('В скрипте нет модели',model)
            return None
    except:
        print('End_connection() error.')

def command_writer(user,passw,host,model,tn):

    if 'D-Link' in model:
        tn.write(b'show lldp rem 25-28\r')
        with open (ip+'.txt', 'w') as f:
            f.write(tn.read_until(b'#', timeout=5).decode('ascii','ignore'))

    elif 'Huawei' in model:
        tn.write(b'display lldp ne\r')
        with open (ip+'.txt', 'w') as f:
            f.write(tn.read_until(b'>', timeout=5).decode('ascii'))

    elif 'Tp-Link' in model:
        tn.write(b'show lldp ne int\r')
        with open (ip+'.txt', 'w') as f:
            f.write(tn.read_until(b'#', timeout=5).decode('ascii'))

    elif model['Maipu']:
        pass
    else:
        print('В скрипте нет модели',model)
        return None

def mku_checker(lldp_ip):
    '''На вход поступает вывод команды sh lldp neighboors. Ищет в нём mku. 
    Если нашёл, возвращает True.'''

    if 'D-Link DGS' in lldp_ip:
        return True
    else:
        return False

def mku_finder(user,passw,host,model,tn):
    if 'D-Link' in model:
        tn.write(b'show lldp rem 25-28\r')
        with open (ip+'.txt', 'w') as f:
            f.write(tn.read_until(b'#', timeout=5).decode('ascii','ignore'))

def main(ip):
    data = {}
    USER = 'khusainov.if'     #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< CAUTION!!!!
    PASSWORD = keyring.get_password("work_for_switches", "khusainov.if")   #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< CAUTION!!!!
    if ip_ping_checker(ip):
        model_snmp_res = get_model(ip)
        try:
            data.update(model_choicer(model_snmp_res))
            print(ip,'а модель такая: ', model_choicer(model_snmp_res))
            try:
                tn = connector(USER, PASSWORD, ip, data) #It's global now!
                begin_connection(USER, PASSWORD, ip, data, tn)
                command_writer(USER, PASSWORD, ip, data, tn)
                end_connection(USER, PASSWORD, ip, data, tn)
                tn.close()
            except:
                print('Telnet object is None.')
        except:
            pass
    else:
        pass

if __name__ == '__main__':
    ips = []
    with open('ips.txt', 'r') as f:
        for ip in f:
            ip = ip.strip()
            ips.append(ip)
    for ip in ips:
        main(ip)