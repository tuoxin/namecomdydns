import requests
import json
import yaml
import sched
import time
import logging

CONFIG_PATH = '/config/'
schedule = sched.scheduler(time.time, time.sleep)

# https://curl.trillworks.com/     Convert curl syntax to Python, Node.js, PHP, R! Great!

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class NameDnsUpdater:

    def __init__(self):
        self.username = ''
        self.token = ''
        self.domain = ''
        self.host = ''
        self.recordID = 0
        self.recordIP = ''
        self.ip = ''
        self.configOk = False

    def loadconfig(self):

        # TODO 考虑文件不存在的情况，报错
        try:
            # f = open(r'C:\Users\taxin520\Desktop\dnsupdater.yml', encoding="utf-8")
            f = open(CONFIG_PATH + 'dnsupdater.yml', encoding="utf-8")
            config_data = yaml.load(f)
        except IOError:
            logger.info('LoadConfig IOError Exception')
            return
        except yaml.YAMLError as e:
            logger.info('LoadConfig Unknow Exception' + str(e))
            return

        # TODO: 需要考虑失败的情况
        self.username = config_data['record']['username']
        self.token = config_data['record']['token']
        self.host = config_data['record']['host']
        self.domain = config_data['record']['domain']

        self.configOk = True

    def getdnsrecord(self):
        # curl -u 'name:token'
        # 'https://api.name.com/v4/domains/onecore.life/records'
        # 从上面的返回结果中解析出对应host的ID
        try:
            request_url = 'https://api.name.com/v4/domains/' + self.domain + '/records/'
            response = requests.get(request_url,
                                    auth=(self.username, self.token))
        except requests.exceptions.RequestException as e:
            logger.info('GetDNSRecord Request Failed' + str(e))
            return False

        if response.status_code == 200:
            records = json.loads(response.content)['records']

            for record in records:
                if record['domainName'] == self.domain and record['host'] == self.host:
                    self.recordID = record['id']
                    self.recordIP = record['answer']
                    logger.info('GetDNSRecord ID=' + str(self.recordID))
                    logger.info('GetDNSRecord IP=' + str(self.recordIP))
                    return True
        else:
            logger.info('GetDNSRecord Failed response.status_code=' + str(response.status_code))

        return False

    def updatednsrecord(self):
        if self.recordID != 0:
            # curl -u 'name:token'
            # 'https://api.name.com/v4/domains/example.org/records/588789887' -XPUT
            # --data '{"host":"example","type":"A","answer":"1.1.1.1","ttl":300}'
            # 从上面URL里更新并检查结果
            data = dict()
            data['host'] = self.host
            data['type'] = 'A'
            data['answer'] = self.ip
            data['ttl'] = 300

            data_json = json.dumps(data)

            request_url = 'https://api.name.com/v4/domains/' + self.domain + '/records/' + str(self.recordID)
            try:
                response = requests.put(request_url, data=data_json,
                                        auth=(self.username, self.token))
            except requests.exceptions.RequestException as e:
                logger.info('UpdateDNSRecord Request Failed' + str(e))
                return

            if response.status_code == 200:
                logger.info('Update Succeed IP=' + self.ip)
            else:
                logger.info('Update Succeed IP=' + self.ip + 'Failed Http Code=' + str(response.status_code))

        else:
            self.creatednsrecord()

    def creatednsrecord(self):
        if self.recordID == 0:
            # curl -u 'name:token'
            # 'https://api.name.com/v4/domains/example.org/records' -XPOST
            # --data '{"host":"example","type":"A","answer":"1.1.1.1","ttl":300}'

            data = dict()
            data['host'] = self.host
            data['type'] = 'A'
            data['answer'] = self.ip
            data['ttl'] = 300

            data_json = json.dumps(data)

            request_url = 'https://api.name.com/v4/domains/' + self.domain + '/records/'
            try:
                response = requests.post(request_url, data=data_json,
                                         auth=(self.username, self.token))
            except requests.exceptions.RequestException as e:
                logger.info('CreateDNSRecord Request Failed' + str(e))
                return

            if response.status_code == 200:
                record = json.loads(response.content)
                self.recordID = record['id']

    @staticmethod
    def getcurrentip():
        # curl http://ipecho.net/plain
        # curl http://metadata.tencentyun.com/meta-data/public-ipv4
        try:
            response = requests.get('http://metadata.tencentyun.com/meta-data/public-ipv4')
        except requests.exceptions.RequestException as e:
            logger.info('GetCurrentIP Request Failed' + str(e))
            return

        currentip = ''
        if response.status_code == 200:
            ipbytes = response.content
            currentip = ipbytes.decode()
            logger.info(currentip)
        else:
            logger.info('GetCurrentIP Failed response.status_code=' + str(response.status_code))

        return currentip

    def update(self):
        # TODO 还需要考虑record不存在的情况
        if not self.configOk:
            return

        newip = self.getcurrentip()

        if newip == '':
            logger.info('IP Get Failed, Keep it')
            return

        if self.ip == newip:
            logger.info('IP Not Changed, Keep it')
            return

        self.ip = newip
        if self.getdnsrecord() and self.recordIP != self.ip:
            self.updatednsrecord()
        else:
            if self.recordIP == self.ip:
                logger.info('IP same as record, Keep it')
            else:
                logger.info('Request Failed, Keep it')

    def run(self):
        self.loadconfig()
        self.runintime()

    def runintime(self):
        self.update()
        schedule.enter(60, 0, self.runintime)


def main():
    dns = NameDnsUpdater()
    dns.run()
    schedule.run()


if __name__ == '__main__':
    main()
