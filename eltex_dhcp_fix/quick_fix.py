from eltex_dhcp_conf import *
from base_for_others.switch_management_refactoring import *


def comm_maker(pvids):
    with open('response.txt', 'r') as f:
        text = f.read()
    regex_for_get_dhcp_vlan_snoop = r'VLAN\s+:\s+(\d+)'
    vlans = re.findall(regex_for_get_dhcp_vlan_snoop,text)
    vlans = set(vlans)
    pvids = set(pvids)
    delete_vlans = list(vlans-pvids)
    with open('result.txt', 'w') as f:
        f.write(f'conf t\r')
        for vlan in delete_vlans:
            f.write(f'vlan {vlan}\rno ip dhcp snooping\r')
        for vlan in pvids:
            if int(vlan) in range(1000,1500) or int(vlan) in range(100,801,100):
                f.write(f'vlan {vlan}\rip dhcp snooping\r')
        f.write(f'end\r')
        f.write(f'copy r s\r')
    

def cancel_vlan_dhcp_commands(tn,pvids_for_check):
    '''Проверяет настройки снупинга и удаляет их, если не соответствуют запросу snmp. '''

    #commands_for_get_dhcp_status = ['show ip dhcp snooping | grep VLAN\r',]
    
    tn.write(b'show ip dhcp snooping | grep VLAN\r')
    tn.write(b'\r')
    tn.write(b'\n')
    tn.write(b'\n')
    tn.write(b'\n')
    tn.write(b'\n')
    tn.write(b'\n')
    response = tn.read_until(b'#', timeout=15).decode('ascii','ignore')
    regex_for_get_dhcp_vlan_snoop = r'VLAN\s+:\s+(\d+)'
    vlans = re.findall(regex_for_get_dhcp_vlan_snoop,response)
    print(vlans)
    return tn,vlans

def main(ip):
    ''' Основной ход программы '''

    USER = 'khusainov.if'     #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< CAUTION!!!!
    PASSWORD = keyring.get_password("work_for_switches", "khusainov.if")   #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< CAUTION!!!!

    if ip_ping_checker(ip):
        try:
            pvid = snmp_get_next(ip,'1.3.6.1.2.1.17.7.1.4.5.1.1')
            pvids = list(pvid.values())[0:24]
            tn, data = full_connection(USER, PASSWORD, ip)
            comm_maker(pvids)
            with open('result.txt', 'r') as f:
                for string in f:
                    tn.write(string.encode('ascii'))
                    tn.read_until(b'#', timeout=30).decode('ascii','ignore')
        except Exception as err:
            print(err)
        finally:
            end_connection(USER,PASSWORD,ip,data,tn)
            print('Got vlans')

if __name__ == "__main__":
    ips = []
    pool = ThreadPool()
    pool.map(main, ips)
    pool.close()
    pool.join()
    #map(main,ips)