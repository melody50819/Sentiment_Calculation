from __future__ import unicode_literals
import re
import jieba
import jieba.posseg
import jieba.analyse
import pandas as pd
import pymssql
import pyodbc

def getDict(which):
    conn = pymssql.connect(server='127.0.0.1', user='sa', password='Aqwe123', charset='utf8', database='SD', port='1433')
    cursor = conn.cursor(as_dict=True)
    
    pos_dict = mergeDict('正面詞')
    neg_dict = mergeDict('負面詞')
    neu_dict = mergeDict('中性詞')
    level_dict = mergeDict('程度詞')
    den_dict = mergeDict('否定詞')

    sentiments_dict = {**pos_dict,**neg_dict,**neu_dict}
    levels_dict = {**level_dict}
    deny_dict = {**den_dict}
    if which == 'senti':
        return sentiments_dict
    elif which == 'level':
        return level_dict
    elif which == 'deny':
        return deny_dict
    else:
        return '輸入錯誤'
    #連接SQL，建立字典
    
def mergeDict(word):
    sentiments = []
    score = []
    
    sent = cursor.execute('select sentiments from ' + word)
    a = cursor.fetchall()
    for i in a:
        sentiments += i.values()
    
    sco = cursor.execute('select score from ' + word)
    b = cursor.fetchall()
    for j in b:
        score += j.values()

    dictionary = dict(zip(sentiments, score))
    return dictionary
  
  
def cut_word(content): 
    data = str(content)
    stop_words = []
    
    stopword = cursor.execute('select stopword from 停用詞')
    stop = cursor.fetchall()
    for stopword in stop:
        stop_words += stopword.values()
    
    words = jieba.cut_for_search(data, HMM=True)  #false全模式 true默認模式
    words = [w for w in words if w not in stop_words]
    return words


def getUID(): #取得更新者「日誌」資料表中的'植物編號' T開頭
    ID = []
    u_id = cursor.execute('select 植物編號 from 日誌 where 更新 = 1')
    a = cursor.fetchall()
    for i in a:
        ID += i.values()
    print(" ".join(ID))
    #return a

def getUContent(): #取得更新者「日誌」資料表中的'內容'
    content = []
    u_content = cursor.execute('select 內容 from 日誌 where 更新 = 1')
    b = cursor.fetchall()
    for i in b:
        content += i.values()
    return content
    
    
    
    
def getSentiment(content,dictionary): #輸出list資料型態
    level_W = []
    score = 0
    count = 0
    #print(tokens)
    #print('Sentiment words: ')
    for w in content:
        #print(w)
        if w in dictionary.keys():
            score += dictionary[w]
            #print('%s %s' %(w, sentiments_dict[w]))
            count += 1

            level_W.append(dictionary[w])
    if count != 0:
        return level_W
    else:
        return level_W 

      
def getLevelWords(senti_score,content,dictionary): #程度詞
    res = 0
    level_score = []
    count = 0
    #print(senti_score)
    #print('\n讀到的句子: ', content)
    #print('\nLevel words: ')
    for w in content:
        if w in dictionary.keys():
            level_score.append(dictionary[w])
            print(w) 
            total_score = list(map(lambda x, y:x * y, senti_score, level_score)) #兩個 list 相乘
            count += 1
            #print('%s %s' %(w, levels_dict[w]))
    #判斷有程度詞
    if count != 0:      
        #null值補1.0
        while(len(senti_score) != len(level_score)):
            if (len(senti_score) > len(level_score)):
                level_score.append(1.0)
                total_score = list(map(lambda x, y: x * y, senti_score, level_score))
            elif (len(senti_score) <= len(level_score)):
                senti_score.append(1.0)
                total_score = list(map(lambda x, y: x * y, senti_score, level_score))
        #print(len(senti_score),len(level_score))
        #print(level_score)
    #無程度詞
    else:
        #print(level_score)
        #level_score 全部補1.0
        if len(senti_score):
            for i in range(len(senti_score)):
                level_score.append(1.0)
                total_score = list(map(lambda x, y: x * y, senti_score, level_score))
        else:
            total_score = []     
    return total_score

#判斷有幾個否定詞


def getDenyCount(content,dictionary): #否定詞個數
    count = 0
    total_score = []
    #print(w)
    for w in content:
        if w in dictionary.keys():
            count += 1
    return count

def getDenyWords(num,content,dictionary): #否定詞
    total_list = []
    #print(type(sentence)) #list
    for i in content:
        if num % 2 == 0: #偶數
            i *= 1.0
        elif num % 2 != 0: #奇數
            i *= -1.0
        else:
            i *= 1.0
        total_list.append(i)
    return total_list

  
def computeScore(total_list): #計算活力值和成長值
    res = 0
    all_score = 0
    for i in total_list:
        res += i
        if res >= 5.0:
            res = 5.0
        elif res <= -5.0:
            res = -5.0
    count = len(total_list)         
    #print('\ntotal score :' , res)
    if count > 0:
        avg = round(res / count, 1)
    else:
        avg = 0
    #print('平均後總分: ',avg)
    energy = int(50 + (avg * 10))
    growth = energy/4
    #print('Energy value = '+ str(energy) + ' %')
    if avg >= 0:
        all_score = (energy,growth)
        return all_score
    else:
        all_score = (energy,growth)
        return all_score
        
        

def updateSQL(energy,growth):
    conn = pymssql.connect(server='127.0.0.1', user='sa', password='Aqwe123', charset='utf8', database='SD', port='1433') 
    
    e_update = cursor.execute('update 植物 set 活力值 = %s where 植物編號 = %s',energy,getUID())
    g_update = cursor.execute('update 植物 set 成長值 = %s where 植物編號 = %s',energy,getUID())
    conn.commit()   

    
def main():
    sentence = cut_word(getUContent())
    senti = getSentiment(sentence,getDict('senti')) #正負面、中性詞
    level = getLevelWords(senti,sentence,getDict('level')) #程度詞
    dWord_num = getDenyCount(sentence,getDict('deny')) #否定詞個數
    deny = getDenyWords(dWord_num,level,getDict('deny')) #否定詞
    
    print(computeScore(deny)) #計算分數 #tuple
    energy = computeScore(deny)[0]
    growth = computeScore(deny)[1]
    
    #sql = "update 日誌 set 更新 = 0 where 植物編號 = %s" % getUID()
    update = cursor.execute('update 日誌 set 更新 = 0 where 植物編號 =%s',getUID())
    conn.commit()
    updateSQL()
    conn.commit()
    

    
if __name__ == '__main__':
    main()