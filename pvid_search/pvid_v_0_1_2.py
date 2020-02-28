from pysnmp.entity.rfc3413.oneliner import cmdgen
import re
import socket
from time import time, localtime, strftime
from datetime import datetime, timedelta
import json
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool

def snmp_get_next(ip,OID,community = 'holding08',port = 161,standalone_value=False):
    '''Аналог команды snmpwalk. На вход IP адрес и OID, который надо итерировать.
    Возвращает словарь, где ключ это число следующее за поданным на вход OID, 
    а значение ключа данные хранящиеся в этом OID
    standalone_value отвечает за флаг для того, чтобы получить одно значение в итерации.
    В этом случае возвращает словарь с ip адресом и значением OID'''

    res = {}
    cmdGen = cmdgen.CommandGenerator()
    errorIndication, errorStatus, errorIndex, varBindTable = cmdGen.nextCmd(cmdgen.CommunityData('holding08'),
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
        print(ip, 'error')
        
def comand_gen_dlink(pvid_dict):
    '''На вход поступает словарь вида порт:влан.
    На выходе имеем сгенерированные команды для конкретного узла.'''

def checkswmgmt(ip,timeout=2):
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

def ipoe_l2_searcher(json_obj):
    '''На вход поступает json-объект(на самом деле пока словарь), затем в нём ищется любой порт с 38XX и 39XX
    Эти порты проверяются на предмет активности. Если её нет в течение аптайма коммутатора, 
    то идёт подключение к МКУ для выяснения stp метки. 
    Затем в файле с брасом происходит поиск названия компании, происходит транслитерация 
    В отдельный файл записывается результат вида {ip:{port:vlan, tag:[rusname, name]}}'''

    res = {}
    for ip,v in json_obj.items():
        for port, vlan in v['PVID'].items():
            if vlan in IPOE_VLANS:
                in_traffic_oid = '1.3.6.1.2.1.2.2.1.10' #+ str(port)
                out_traffic_oid = '1.3.6.1.2.1.2.2.1.16'
                in_traf = snmp_get_next(ip,in_traffic_oid) #, standalone_value=True
                out_traf = snmp_get_next(ip,out_traffic_oid)
                if in_traf[port] == '0' or out_traf[port] == '0':
                    res[ip]={port:vlan}
                    if 'TAG' not in res[ip]:
                        tag = stp_tag_searcher(ip)
                        res[ip].update({'TAG':tag+'.'+vlan})
                        if 'UPTIME' not in res[ip]:
                            res[ip].update({'UPTIME':v['UPTIME']})
                        
    return res
            
def stp_tag_searcher(ip):
    '''Подключается к брасу и смотрит метку.'''

    ip = re.match(r'((?:\d+\.){3})',ip).group() +'254'
    oid_for_stp_mst_name = '1.3.6.1.4.1.171.12.15.2.1'
    result = snmp_get_next(ip,oid_for_stp_mst_name,standalone_value=True)
    return result

def company_name_searcher():
    '''Ищет совпадения в конфиге браса'''

def main_fun(ip):
    '''На вход поступает IP адрес. На выходе файл с названиями компаний'''
    try:
        if checkswmgmt(ip):
                res = {}
                ipoe_l2_without_traf = {}
                res[ip]={'MODEL':snmp_get_next(ip,model_oid,standalone_value = True)}
                res[ip].update(dlink_request(ip,dlink_oids))
                print(ip, 'checked.')
                ipoe_l2_without_traf = ipoe_l2_searcher(res)
                if ipoe_l2_without_traf:
                    print('This is empty', ipoe_l2_without_traf)
                    with open('no_traffic.json', 'a') as r:
                        r.write(json.dumps(ipoe_l2_without_traf,sort_keys=True, indent=2)+'\n')

                with open('res.json', 'a') as f:
                    f.write(json.dumps(res,sort_keys=True, indent=2)+'\n')
        else:
            print(ip, 'is unreachable.')
    except:
        print(ip, 'ERROR')

#---------------------------------------------------------VLAN_DATABASE--------------------------------------------------------- 
IPOE_VLANS = list(range(3800, 4000))
IPOE_VLANS =list(map(str,IPOE_VLANS))
#------------------------------------------------------END_OF_VLAN_DATABASE------------------------------------------------------
model_oid = '1.3.6.1.2.1.1.1'
dlink_oids = {
        'HOSTNAME': '1.3.6.1.2.1.1.5',
        'PVID': '1.3.6.1.2.1.17.7.1.4.5.1.1',
        'UPTIME':'1.3.6.1.2.1.1.3'
    }

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

if __name__ == '__main__':
    start_time = time()
    result = []
    ips = []
    gen = (row for row in open('final_without_some.txt'))
    start = 0
    step = 11
    while start < 7370:
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
        pool.map(main_fun, ips)
        pool.close()
        pool.join()
        step +=step

    finish_time = time()
    time_range = timedelta(seconds=(finish_time - start_time))
    print(time_range)
