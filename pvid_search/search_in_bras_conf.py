import re 

with open('traf.txt', 'r') as f, open('tag_desc.txt', 'a') as res:
    for line in f:
        print(line)
        string_list = line.split(' ')
        almost_tag = string_list[5]
        tag_list = almost_tag.split(':')
        tag = tag_list[1]
        tag = tag.split('.')
        regex = r'(?:'+tag[0]+r'\[.-]'+tag[1]+r') '+ r'create\s+description "(.+)"'
        regex_tag = r'(?:'+tag[0]+r'\.'+tag[1]+r')'
        regex_desc = r'description "(.+)"'
        #print(regex)
        with open('bras_conf.txt', 'r') as bras:
            for string in bras:
                #print(string)
                result = re.search(regex_tag, string)
                if result:
                    print(result.group())
                    desc_string = (next(bras))
                    description = re.search(regex_desc, desc_string)
                    if description:
                        print(description.group())
                    else:
                        print('No description.')
                    res.write(line)
                    if description:
                        res.write(description.group())
                        res.write('\n\n')
                    continue
                else:
                    continue


            '''
        except:
            print('No matches:', tag)
            res.write(line)
            res.write('No matches in bras conf '+tag+'.\n')'''
    print('Done.')