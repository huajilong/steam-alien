# encoding:UTF-8
# python3.6
import requests
import sys
import os
import re
import time
from threading import Thread, Event
from multiprocessing.dummy import Pool as ThreadPool
import random

difficulty_dict = ['低', '中', '高', 'Boss']
score_dict = ['600', '1200', '2400', '???']
best_update = None
bestupdater_flag = 1
updater_ready = Event()
BASE_URL = 'https://community.steam-api.com/ITerritoryControlMinigameService/{}/v0001?language=schinese'
headers = {
    'Accept': '*/*',
    'DNT': '1',
    'Origin': 'https://steamcommunity.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36',
    'Referer': 'https://steamcommunity.com/saliengame/play/'
}


def load():
    if os.path.exists('token.txt'):
        users = []
        with open('token.txt', 'r', encoding="utf-8") as f:
            lines = f.readlines()
            flen = len(lines)
            for i in range(flen):
                if lines[i][0] == '#':
                    print('忽略#开头的行：', lines[i].strip('\n'))
                    continue
                data = lines[i].strip('\n').split('+')
                if len(data) == 3:
                    user = [data[0], data[1], data[2]]
                elif len(data) == 1:
                    name = data[0][-4:]
                    user = [name, data[0], data[1]]
                users.append(user)
        return users
    else:
        with open('token.txt', 'w', encoding="utf-8") as f:
            f.write(
                'bot1+token+Steam64Id\nbot2+token+Steam64Id\nbot3+token+Steam64Id')
        return False


def gettime():
    t=int(time.time())
    return t

def get_planets():
    r = requests.get(BASE_URL.format('GetPlanets'),
                     params={"active_only": "1"}, headers=headers)
    planets = r.json()['response']['planets']

    def exp(p):
        return p if not p['state']['captured'] else False
    planets = sorted(filter(exp, planets),
                     key=lambda p: p['state']['capture_progress'])
    return planets


def getzone(planet_id):
    try:
        r = requests.get(BASE_URL.format('GetPlanet'), params={
                         'id': '{}'.format(planet_id)}, headers=headers)
    except Exception as e:
        print('getzone|Error:', e)
    data = r.json()['response']['planets'][0]
    name = data['state']['name']
    zones = data['zones']

    def real(zone):
        if zone.__contains__('capture_progress') and not zone['captured']:
            return True
        else:
            False
    zones = list(filter(real, zones))

    boss_zones = []
    boss_zones = sorted((z for z in zones if z['type']
                         == 4 and z['boss_active']), key=lambda x: x['zone_position'])
    if boss_zones:
        print(time.strftime("%H:%M:%S", time.localtime())," |在{}发现Boss!".format(name))
        for z in boss_zones:
            z['difficulty'] = 4
    else:
        zones.sort(key=lambda z: z['capture_progress'])
        pass

    def exp(z):
        return z if 0 < z['capture_progress'] < 0.95 and z['type'] != 4 else False
    others = sorted(filter(exp, zones),
                    key=lambda z: z['difficulty'], reverse=True)
    return boss_zones+others


def update_dict(planet,zone):
    select={}
    select['gameid']=zone['gameid']
    select['zone_position'] = zone['zone_position']
    select['difficulty'] = zone['difficulty']
    select['zone_progress'] = zone['capture_progress']
    select['id'] = planet['id']
    select['name'] = planet['state']['name']
    select['planet_progress'] = planet['state']['capture_progress']
    return select



def getbest():
    select = {'difficulty': 0}
    planets = get_planets()
    for planet in planets:
        zones = getzone(planet['id'])
        planet['zones'] = zones
        if zones:
            if zones[0]['difficulty'] > select['difficulty']:
                zone = zones[0]
                select=update_dict(planet,zone)
    if select['difficulty'] == 1:
        planets.reverse()
        for planet in planets:
            zones = planet['zones']
            if zones:
                zone = zones[0]
                select=update_dict(planet,zone)
                break
    if select:
        return select
    else:
        print('Getbest functinon erro')
        return False


def bestupdater():
    global best_update
    erro = 0
    while(bestupdater_flag):
        try:
            if best_update != None and best_update['difficulty'] == 4:
                try:
                    r = requests.get(BASE_URL.format('GetPlanet'), params={
                                     'id': '{}'.format(best_update['id'])}, headers=headers)
                except Exception as e:
                    print('bestupdater|Error:', e)
                zones = r.json()['response']['planets'][0]['zones']
                zone = zones[best_update['zone_position']]
                if zone['boss_active']:
                    time.sleep(20)
                    continue
            result = getbest()
            if result != {"response": {}}:
                best_update = result
                if not updater_ready.isSet():
                    updater_ready.set()
                # print('调试信息|bestupdater|',result)
                if result['zone_progress'] > 0.9:
                    time.sleep(30)
                elif result['zone_progress'] > 0.8:
                    # print(time.strftime("%H:%M:%S", time.localtime()),
                    #       '调试信息|bestupdater|', result)
                    time.sleep(60)
                # elif result['difficulty'] == 4:
                #     time.sleep(60)
                else:
                    time.sleep(random.randint(90, 110))
            elif erro < 5:
                erro += 1
                print('寻找最佳星球失败,10s后重试')
                time.sleep(10)
            elif erro >= 5:
                erro = 0
                print('寻找最佳星球失败次数过多,20s后重试')
                time.sleep(20)
        except Exception as e:
            print('寻找最佳星球失败|Error:', e)


class worker:
    def __init__(self, data):
        self.accountid = int(data[2]) - 76561197960265728
        self.access_token = data[1]
        self.botname = data[0]
        self.playerinfo = {}
        self.planet_id = ''
        self.best = {}
        self.OldScore = 0
        self.lag = 0

    def timestamp(self):
        t = time.strftime("%H:%M:%S", time.localtime())
        return'{} |{} |'.format(t, self.botname)

    def bestupdate(self, data):
        self.best = data

    def joinplanet(self, planet_id):
        requests.post(BASE_URL.format('JoinPlanet'), params={
                      'id': planet_id, 'access_token': self.access_token}, headers=headers)

    def leave(self, gameid):
        requests.post('https://community.steam-api.com/IMiniGameService/LeaveGame/v0001/',
                      params={'gameid': gameid, 'access_token': self.access_token}, headers=headers)

    def get_playerinfo(self, output=False):
        r = requests.post(BASE_URL.format('GetPlayerInfo'),
                          data={'access_token': self.access_token}, headers=headers)
        self.playerinfo = r.json()['response']
        self.OldScore = int(self.playerinfo['score'])
        if output:
            info = 'level:{} 经验:{}/{}'.format(
                self.playerinfo['level'], self.playerinfo['score'], self.playerinfo['next_level_score'])
            print(self.timestamp(), info)

    def fightboss(self):
        # print(self.timestamp(),'调试信息|uploadboss|')
        bossFailsAllowed = 10
        nextheal = 9999999999999
        WaitingForPlayers = True
        damageToBoss=lambda x: 0 if x else 1
        MyScoreInBoss = 0
        BossEstimate = {
            'PrevHP': 0,
            'PrevXP': 0,
            'DeltHP': [],
            'DeltXP': [],
        }
        while True:
            useHeal = 0
            damageTaken = 0
            if gettime() >= nextheal:
                UseHeal = 1
                nextheal = gettime() + 120
                print(self.timestamp(), 'Boss战|使用治愈能力')
            data = {
                'access_token': self.access_token,
                "use_heal_ability": useHeal,
                "damage_to_boss": damageToBoss(WaitingForPlayers),
                "damage_taken": damageTaken
            }
            r = requests.post(BASE_URL.format('ReportBossDamage'), data=data, headers=headers)
            eresult = int(r.headers['X-eresult'])
            result = r.json()['response']
            if eresult == 11:
                print(self.timestamp(), 'Boss战|InvalidState')
                break
            if eresult != 1:
                print(self.timestamp(), eresult, r.headers['X-error_message'])
                bossFailsAllowed -= 1
                if bossFailsAllowed < 1:
                    print(self.timestamp(), 'Boss战|错误次数过多，退出')
                    break
            if result.__contains__('boss_status'):
                if not result['boss_status'].__contains__('boss_players'):
                    print(self.timestamp(), 'Boss战|等待中')
                    continue
            else:
                continue
            if result.__contains__('waiting_for_players'):
                if result['waiting_for_players']:
                    WaitingForPlayers = True
                    print(self.timestamp(), 'Boss战|等待其他玩家')
                    continue
                else:
                    WaitingForPlayers = False
                    nextheal = gettime() + random.randint(0, 120)
            boss_status = result['boss_status']
            boss_players = boss_status['boss_players']
            myplayer = None
            for player in boss_players:
                if player["accountid"] == self.accountid:
                    myplayer = player
                    break
            if myplayer != None:
                MyScoreInBoss = int(myplayer['score_on_join']) + int(myplayer['xp_earned'])
                info = "Boss战|玩家血量: {}/{}|现在的等级为：{} => {} 经验：{}|获得的经验: {} (仅供参考）".format(
                    myplayer["hp"], myplayer["max_hp"], myplayer["level_on_join"], myplayer['new_level'], MyScoreInBoss, myplayer["xp_earned"])
                print(self.timestamp(), info)
            info = "Boss战|Boss血量: {}/{} Lasers: {} 团队治疗量: {}".format(
                boss_status['boss_hp'], boss_status['boss_max_hp'], result['num_laser_uses'], result['num_team_heals'])
            print(self.timestamp(), info)
            if result.__contains__('game_over'):
                if result['game_over']:
                    break
            if BossEstimate['PrevXP'] > 0:
                BossEstimate['DeltHP'].append(
                    abs(BossEstimate['PrevHP']-int(boss_status['boss_hp'])))
                if myplayer != None:
                    BossEstimate['DeltXP'].append(
                        abs(int(myplayer['xp_earned'])-BossEstimate['PrevXP']))
                else:
                    BossEstimate['DeltXP'].append(1)
                if myplayer != None:
                    EstXPRate = sum(
                        BossEstimate['DeltXP'])/len(BossEstimate['DeltXP'])
                else:
                    EstXPRate = 2500
                EstBossDPT = sum(
                    BossEstimate['DeltHP'])/len(BossEstimate['DeltHP'])
                EstXPTotal = (
                    int(boss_status['boss_max_hp'])/EstBossDPT) * EstXPRate
                info = 'Boss战|预计获得的总经验：{:.2} 速度为：{:.2}xp/每次 DPS:{:.2}/s'.format(
                    EstXPTotal, EstXPRate, EstBossDPT/5)
                print(self.timestamp(), info)
            BossEstimate['PrevHP'] = int(boss_status['boss_hp'])
            if myplayer != None:
                BossEstimate['PrevXP'] = int(myplayer['xp_earned'])
            else:
                BossEstimate['PrevXP'] = 0
            time.sleep(5)
        if MyScoreInBoss > 0:
            info = '====Boss战后，你的经验：{} 获得的经验：{} ===='.format(
                MyScoreInBoss, MyScoreInBoss-self.OldScore)
            self.OldScore = MyScoreInBoss
            print(self.timestamp(), info)
        return True

    def joinbosszone(self):
        try:
            data={'zone_position': str(self.best['zone_position']), 'access_token': self.access_token, }
            r = requests.post(BASE_URL.format('JoinBossZone'), data=data, headers=headers)
            eresult=int(r.headers['X-eresult'])
            if eresult != 1:
                print(self.timestamp(), '加入Boss地区失败|',r.headers['X-error_message'])
                return False
            else:
                time.sleep(4)
                return True
        except Exception as e:
            print(self.timestamp(), '加入Boss游戏失败|Error:', e)
            return False

    def upload(self, score):
        try:
            r = requests.post(BASE_URL.format('ReportScore'), data={
                              'access_token': self.access_token, 'score': score}, headers=headers)
            result = r.json()['response']
            if result.__contains__('new_score'):
                print(self.timestamp(), '分数发送成功，目前经验值：{}'.format(
                    result['new_score']))
                return True
            else:
                pattern=re.compile(r'\d{10}')
                result=pattern.findall(r.headers['X-error_message'])
                getlag=False
                if result!=[]:
                    t=(int(result[1])-int(result[0]))/(110+self.lag)*(110-int(result[1])+int(result[0]))
                    self.lag=int(t)
                    print('延时：{}s'.format(self.lag))
                if 'which is too soon' in r.headers['X-error_message']:
                    print(self.timestamp(), '由于速度过快，分数发送失败')
                    return True
                elif 'which is too late' in r.headers['X-error_message']:
                    print(self.timestamp(), '由于速度过慢，分数发送失败')
                    return True
                else:
                    print(self.timestamp(), '分数发送失败', r.headers['X-error_message'])
                return False
        except Exception as e:
            print(self.timestamp(), '分数发送失败|Error:', e)
            return False

    def play(self):
        zone_position = self.best['zone_position']
        score = score_dict[self.best['difficulty']-1]
        try:
            r = requests.post(BASE_URL.format('JoinZone'), data={
                              'zone_position': str(zone_position), 'access_token': self.access_token, }, headers=headers)
        except Exception as e:
            print(self.timestamp(), '加入游戏失败|Error:', e)
            time.sleep(11)
            return False
        try:
            if r.json()['response'].__contains__('zone_info'):
                print(self.timestamp(), '已成功加入，等待{}s发送分数'.format(110+self.lag))
                time.sleep(110+self.lag)
                erro = 0
                while erro < 4:
                    if self.upload(score):
                        return True
                    else:
                        print(self.timestamp(), 'wait 5s')
                        time.sleep(5)
                        erro = erro+1
                else:
                    print(self.timestamp(), '分数发送失败已达4次，休息20s')
                    time.sleep(20)
                    return False
            else:
                print(self.timestamp(), '加入游戏失败|',
                      r.headers['X-error_message'])
                match = re.search(r'\d+', r.headers['X-error_message'])
                if match != None:
                    self.leave(match.group())
                time.sleep(10)
                return False
        except Exception as e:
            print(self.timestamp(), '加入游戏失败|Error:', e)
            self.reset(True, False, False)
            return False

    def reset(self, resetzone=True, resetplanet=True, output=True, planet_id=False):
        self.get_playerinfo(output)
        playerinfo = self.playerinfo
        if playerinfo.__contains__('active_zone_game') and resetzone:
            self.leave(playerinfo['active_zone_game'])
            print(self.timestamp(), '离开房间:{}'.format(
                playerinfo['active_zone_game']))
        elif playerinfo.__contains__('active_boss_game') and resetzone:
            self.leave(playerinfo['active_boss_game'])
            print(self.timestamp(), '离开Boss房间:{}'.format(
                playerinfo['active_boss_game']))
        if playerinfo.__contains__('active_planet') and resetplanet:
            self.leave(playerinfo['active_planet'])
            print(self.timestamp(), '离开星球:{}'.format(
                playerinfo['active_planet']))
        else:
            pass
        if planet_id and planet_id != playerinfo['active_planet']:
            self.leave(playerinfo['active_planet'])
            print(self.timestamp(), '离开星球:{}'.format(
                playerinfo['active_planet']))
        else:
            pass

    def loop(self):
        self.get_playerinfo(True)
        self.bestupdate(best_update)
        z_d = self.best['difficulty']
        if self.playerinfo.__contains__('active_planet'):
            self.planet_id = self.playerinfo['active_planet']
        else:
            self.planet_id = None
        if self.best['id'] != self.planet_id:
            if self.planet_id:
                self.leave(self.planet_id)
            else:
                pass
            self.planet_id = self.best['id']
            self.joinplanet(self.planet_id)
        else:
            pass
        planet_info = '星球id：{}  星球名：{}  进度：{}'.format(
            self.best['id'], self.best['name'], self.best['planet_progress'])
        print(self.timestamp(), planet_info)
        zone_info = '已选择房间 {}(进度：{})，难度为：{}，预计获得的分数:{}'.format(
            self.best['zone_position'], self.best['zone_progress'], difficulty_dict[z_d-1], score_dict[z_d-1])
        print(self.timestamp(), zone_info)
        if z_d < 4:
            self.play()
            self.reset(True, False, False)
        else:
            if self.joinbosszone():
                self.fightboss()




def handler(user):
    planet_id = 0
    bot = worker(user)
    bot.reset()
    updater_ready.wait()
    print(time.strftime("%H:%M:%S", time.localtime()),
          '线程：{} 已就绪'.format(user[0]))
    while(1):
        try:
            bot.loop()
        except Exception as e:
            t = time.strftime("%H:%M:%S", time.localtime())
            print('{} | {}|Error:'.format(t, user[0]), e)


def main():
    users = load()
    if not users:
        print('please check token.txt')
        return False
    planet_id = False
    updater = Thread(target=bestupdater)
    updater.start()
    pool = ThreadPool(len(users))
    print(time.strftime("%H:%M:%S", time.localtime()), 'starting,please wait')
    pool.map(handler, users)
    pool.close()
    pool.join()
    bestupdater_flag = 0
    updater.join()


if __name__ == '__main__':
    main()
