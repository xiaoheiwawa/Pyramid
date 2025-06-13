# -*- coding: utf-8 -*-
# by @嗷呜
import json
import re
import sys
from urllib.parse import urlparse

import requests
from pyquery import PyQuery as pq
from base64 import b64decode, b64encode
from requests import Session
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    def init(self, extend=""):
        try:self.proxies = json.loads(extend)
        except:self.proxies = {}
        self.session = Session()
        self.session.proxies.update(self.proxies)
        self.session.headers.update(self.headers)
        pass

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    host = "https://www.xvideos.com"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5410.0 Safari/537.36",
        "pragma": "no-cache",
        "cache-control": "no-cache",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-ch-ua": "\"Not(A:Brand\";v=\"99\", \"Google Chrome\";v=\"133\", \"Chromium\";v=\"133\"",
        "dnt": "1",
        "origin":host,
        'referer':f'{host}/',
        "sec-ch-ua-mobile": "?0",
        "sec-fetch-site": "cross-site",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "priority": "u=1, i"
    }

    def homeContent(self, filter):
        result = {}
        cateManual = {
            "最新": "/new",
            "最佳": "/best",
            "频道": "/channels-index",
            "标签": "/tags",
            "明星": "/pornstars-index"
        }
        classes = []
        for k in cateManual:
            classes.append({
                'type_name': k,
                'type_id': cateManual[k]
            })
        result['class'] = classes
        return result

    def homeVideoContent(self):
        data = self.getpq()
        return {'list':self.getlist(data(".mozaique .frame-block"))}

    def categoryContent(self, tid, pg, filter, extend):
        vdata = []
        result = {}
        page = f"/{int(pg) - 1}" if pg != '1' else ''
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        if tid=='/new' or 'tags_click' in tid:
            if 'tags_click' in tid:tid=tid.split('click_')[-1]
            data=self.getpq(f'{tid}/{pg}')
            vdata=self.getlist(data(".mozaique .frame-block"))
        elif tid=='/best':
            if pg=='1':
                self.path=self.session.get(f'{self.host}{tid}',allow_redirects=False).headers['Location']
            data=self.getpq(f'{self.path}{page}')
            vdata=self.getlist(data(".mozaique .frame-block"))
        elif tid=='/channels-index' or tid=='/pornstars-index':
            data = self.getpq(f'{tid}{page}')
            vhtml=data(".mozaique .thumb-block")
            for i in vhtml.items():
                a = i('.thumb-inside .thumb a')
                match = re.search(r'src="([^"]+)"', a('script').text())
                img=''
                if match:
                    img = match.group(1).strip()
                vdata.append({
                    'vod_id': f"channels_click_{'/channels'if tid=='/channels-index' else ''}"+a.attr('href'),
                    'vod_name': a('.profile-name').text() or i('.profile-name').text().replace('\xa0','/'),
                    'vod_pic': self.proxy(img),
                    'vod_tag': 'folder',
                    'vod_remarks': i('.thumb-under .profile-counts').text(),
                    'style': {'ratio': 1.33, 'type': 'rect'}
                })
        elif tid=='/tags':
            result['pagecount'] = pg
            vhtml = self.getpq(tid)
            vhtml = vhtml('.tags-list')
            for d in vhtml.items():
                for i in d('li a').items():
                    vdata.append({
                        'vod_id': "tags_click_"+i.attr('href'),
                        'vod_name': i.attr('title') or i('b').text(),
                        'vod_pic': '',
                        'vod_tag': 'folder',
                        'vod_remarks': i('.navbadge').text(),
                        'style': {'ratio': 1.33, 'type': 'rect'}
                    })
        elif 'channels_click' in tid:
            tid=tid.split('click_')[-1]
            vhtml=self.session.post(f'{self.host}{tid}/videos/best/{int(pg)-1}').json()
            for i in vhtml['videos']:
                vdata.append({
                    'vod_id': i.get('u'),
                    'vod_name': i.get('tf'),
                    'vod_pic': self.proxy(i.get('il')),
                    'vod_year': i.get('n'),
                    'vod_remarks': i.get('d'),
                    'style': {'ratio': 1.33, 'type': 'rect'}
                })
        result['list'] = vdata
        return result

    def detailContent(self, ids):
        url = f"{self.host}{ids[0]}"
        data = self.getpq(ids[0])
        vn=data('meta[property="og:title"]').attr('content')
        dtext=data('.main-uploader a')
        href=dtext.attr('href')
        pdtitle=''
        if href and href.count('/') < 2:
            href=f'/channels{href}'
            pdtitle = '[a=cr:' + json.dumps({'id': 'channels_click_'+href, 'name': dtext('.name').text()}) + '/]' + dtext('.name').text() + '[/a]'
        vod = {
            'vod_name': vn,
            'vod_director':pdtitle,
            'vod_remarks': data('.page-title').text().replace(vn,''),
            'vod_play_from': 'Xvideos',
            'vod_play_url': ''
        }
        js_content = data("#video-player-bg script")
        jstr=''
        for script in js_content.items():
            content = script.text()
            if 'setVideoUrlLow' in content and 'html5player' in content:
                jstr = content
                break
        plist = [f"{vn}${self.e64(f'{1}@@@@{url}')}"]
        def extract_video_urls(js_content):
            try:
                low = re.search(r'setVideoUrlLow\([\'"]([^\'"]+)[\'"]\)', js_content)
                high = re.search(r'setVideoUrlHigh\([\'"]([^\'"]+)[\'"]\)', js_content)
                hls = re.search(r'setVideoHLS\([\'"]([^\'"]+)[\'"]\)', js_content)

                return {
                    'hls': hls.group(1) if hls else None,
                    'high': high.group(1) if high else None,
                    'low': low.group(1) if low else None
                }
            except Exception as e:
                print(f"提取视频URL失败: {str(e)}")
                return {}
        if jstr:
            try:
                urls = extract_video_urls(jstr)
                plist = [
                    f"{quality}${self.e64(f'{0}@@@@{url}')}"
                    for quality, url in urls.items()
                    if url
                ]
            except Exception as e:
                print(f"提取url失败: {str(e)}")
        vod['vod_play_url'] = '#'.join(plist)
        return {'list':[vod]}

    def searchContent(self, key, quick, pg="1"):
        data=self.getpq(f'/?k={key}&p={int(pg)-1}')
        return {'list':self.getlist(data(".mozaique .frame-block")),'page':pg}

    def playerContent(self, flag, id, vipFlags):
        ids=self.d64(id).split('@@@@')
        if '.m3u8' in ids[1]: ids[1] = self.proxy(ids[1], 'm3u8')
        return {'parse': int(ids[0]), 'url': ids[1], 'header': self.headers}

    def localProxy(self, param):
        url=self.d64(param['url'])
        if param.get('type') == 'm3u8':
            return self.m3Proxy(url)
        else:
            return self.tsProxy(url)

    def e64(self, text):
        try:
            text_bytes = text.encode('utf-8')
            encoded_bytes = b64encode(text_bytes)
            return encoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64编码错误: {str(e)}")
            return ""

    def d64(self,encoded_text):
        try:
            encoded_bytes = encoded_text.encode('utf-8')
            decoded_bytes = b64decode(encoded_bytes)
            return decoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64解码错误: {str(e)}")
            return ""

    def getlist(self, data):
        vlist=[]
        for i in data.items():
            a=i('.thumb-inside .thumb a')
            b=i('.thumb-under .title a')
            vlist.append({
                'vod_id': a.attr('href'),
                'vod_name': b('a').attr('title'),
                'vod_pic': self.proxy(a('img').attr('data-src')),
                'vod_year': a('.video-hd-mark').text(),
                'vod_remarks': b('.duration').text(),
                'style': {'ratio': 1.33, 'type': 'rect'}
            })
        return vlist

    def getpq(self, path=''):
        response = self.session.get(f'{self.host}{path}').text
        try:
            return pq(response)
        except Exception as e:
            print(f"{str(e)}")
            return pq(response.encode('utf-8'))

    def m3Proxy(self, url):
        ydata = requests.get(url, headers=self.headers, proxies=self.proxies, allow_redirects=False)
        data = ydata.content.decode('utf-8')
        if ydata.headers.get('Location'):
            url = ydata.headers['Location']
            data = requests.get(url, headers=self.headers, proxies=self.proxies).content.decode('utf-8')
        lines = data.strip().split('\n')
        last_r = url[:url.rfind('/')]
        parsed_url = urlparse(url)
        durl = parsed_url.scheme + "://" + parsed_url.netloc
        for index, string in enumerate(lines):
            if '#EXT' not in string:
                if 'http' not in string:
                    domain=last_r if string.count('/') < 2 else durl
                    string = domain + ('' if string.startswith('/') else '/') + string
                lines[index] = self.proxy(string, string.split('.')[-1].split('?')[0])
        data = '\n'.join(lines)
        return [200, "application/vnd.apple.mpegur", data]

    def tsProxy(self, url):
        data = requests.get(url, headers=self.headers, proxies=self.proxies, stream=True)
        return [200, data.headers['Content-Type'], data.content]

    def proxy(self, data, type='img'):
        if data and len(self.proxies):return f"{self.getProxyUrl()}&url={self.e64(data)}&type={type}"
        else:return data
