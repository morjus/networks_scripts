import json

with open('no_traffic.json') as f, open('traf.txt', 'w') as res:
    file_content = f.read()
    templates = json.loads(file_content)
    for item in templates:
        for ip, data in item.items():
            s = 'IP-адрес коммутатора:',ip,'порт',list(data.keys())[0],'TAG:'+data['TAG'],'время неактивности:',data['UPTIME']+'\n'
            string = ' '.join(s)
            #print(string)
            res.write(string)
    print('Done.')