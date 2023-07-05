import os
import shutil
import requests
from time import sleep

from config import *
from settings import *
from modules.files import Files

from flask import request


def get_path_files(path):
    files = os.listdir(path)
    try:
        files.remove('dont_delete.txt')
    except:
        pass

    return files


def do_backup(browser_profile_id):
    if (backup is True):
        shutil.copytree(os.path.join(os.getcwd(), 'browsers', browser_profile_id), os.path.join(os.getcwd(), 'browsers_backup', browser_profile_id), dirs_exist_ok=True)


def send_request(method, url, headers={}, payload={}):
    session = requests.Session()

    headers_dict = dict(headers)

    while True:
        try:
            if (method.lower() == 'get'):
                resp = session.request(method=method.lower(), url=url, headers=headers_dict)
            else:
                resp = session.request(method=method.lower(), url=url, headers=headers_dict, json=payload)

            if (resp.status_code in (200, 401)):
                return resp
            else:
                logger.error(f'Bad request status code: {resp.status_code} | Method: {method} | Response: {resp.text} | Url: {url} | Headers: {headers_dict} | Payload: {payload} | OLD HEADERS: {headers}')

        except Exception as error:
            logger.error(f'Unexcepted error while sending request to {url}: {error}')
            sleep(1)


def check_token_expire(func):
    def wrapper(*args, **kwargs):
        resp = send_request(
            method='GET',
            url=REMOTE_API_BASE_URL + '/profile',
            headers={'Authorization': request.headers['Authorization']},
        )
        if (resp.status_code == 401):
            logger.error(f'METHOD: {request.method} | URL: {request.full_path}')
            return resp.text, resp.status_code

        ret_val = func(*args, **kwargs)

        return ret_val

    wrapper.__name__ = func.__name__
    return wrapper


def sort_profiles(settings, all_profiles):
    def sort_by_notes(d):
        if (d['notes']['content'] is None):
            return '<p></p>'
        return d['notes']['content']

    def sort_by_status(d):
        if ('status' not in d or d['status'] is None):
            return '0'
        return d['status']


    if (settings['sortBy'] == 'status' and settings['order'] == 'DESC'):
        all_profiles['data'].sort(key=sort_by_status, reverse=True)
    elif (settings['sortBy'] == 'status' and settings['order'] == 'ASC'):
        all_profiles['data'].sort(key=sort_by_status)

    elif (settings['sortBy'] == 'notes' and settings['order'] == 'DESC'):
        all_profiles['data'].sort(key=sort_by_notes, reverse=True)
    elif (settings['sortBy'] == 'notes' and settings['order'] == 'ASC'):
        all_profiles['data'].sort(key=sort_by_notes)

    elif (settings['sortBy'] == 'name' and settings['order'] == 'DESC'):
        all_profiles['data'].sort(key=lambda d: d['name'], reverse=True)
    elif (settings['sortBy'] == 'name' and settings['order'] == 'ASC'):
        all_profiles['data'].sort(key=lambda d: d['name'])


    elif (settings['sortBy'] == 'concat_tags' and settings['order'] == 'DESC'):
        all_profiles['data'].sort(key=lambda d: d['tags'], reverse=True)
    elif (settings['sortBy'] == 'concat_tags' and settings['order'] == 'ASC'):
        all_profiles['data'].sort(key=lambda d: d['tags'])

    elif (settings['sortBy'] == 'proxyId' and settings['order'] == 'DESC'):
        all_profiles['data'].sort(key=lambda d: d['proxyId'], reverse=True)
    elif (settings['sortBy'] == 'proxyId' and settings['order'] == 'ASC'):
        all_profiles['data'].sort(key=lambda d: d['proxyId'])


def search_profiles(settings, all_profiles):
    for i in all_profiles['data'][::-1]:
        if (settings['query'] not in i['name']):
            all_profiles['data'].remove(i)


def change_browser_config(changes, browser_profile_id, request):
    browser_profile_info = Files.read_from_file(f'browsers/{browser_profile_id}/info.json')
    browser_profile_info_for_start = Files.read_from_file(f'browsers/{browser_profile_id}/info_for_start.json')

    for i in browser_profile_info['data']:
        try:
            if (type(browser_profile_info['data'][i]) is dict):
                browser_profile_info['data'][i].update(changes[i])
            else:
                browser_profile_info['data'][i] = changes[i]
        except:
            pass
    for i in browser_profile_info_for_start:
        try:
            if (type(browser_profile_info_for_start[i]) is dict):
                browser_profile_info_for_start[i].update(changes[i])
            else:
                browser_profile_info_for_start[i] = changes[i]
        except:
            pass

    if ('proxy' in changes and changes['proxy'] is not None and 'id' in changes['proxy']):
        resp = send_request(
            method='GET',
            url=REMOTE_API_BASE_URL + f"/proxy?ids[0]={changes['proxy']['id']}",
            headers={'Authorization': request.headers['Authorization']}
        )

        info = resp.json()['data'][0]

        prx = {
            "id": info['id'],
            "name": info['name'],
            "type": info['type'],
            "host": info['host'],
            "port": info['port'],
            "login": info['login'],
            "password": info['password'],
            "changeIpUrl": info['changeIpUrl'],
            "savedByUser": 1
        }
        browser_profile_info['data']['proxyId'] = info['id']
        browser_profile_info['data']['proxy'] = prx

        prx = {
            "id": info['id'],
            "name": info['name'],
            "status": None if ('lastCheck' not in info or info['lastCheck'] is None) else info['lastCheck']['status'],
            "ip": info['host'],
            "country": None if ('lastCheck' not in info or info['lastCheck'] is None) else info['lastCheck']['country']
        }
        browser_profile_info_for_start['proxyId'] = info['id']
        browser_profile_info_for_start['proxy'] = prx
    elif ('proxy' in changes and changes['proxy'] is not None and 'id' not in changes['proxy']):
        resp = send_request(
            method='POST',
            url=REMOTE_API_BASE_URL + '/proxy',
            headers={'Authorization': request.headers['Authorization']},
            payload=changes['proxy'],
        )

        info = resp.json()['data']
        prx = {
            "id": info['id'],
            "name": info['name'],
            "type": info['type'],
            "host": info['host'],
            "port": info['port'],
            "login": info['login'],
            "password": info['password'],
            "changeIpUrl": info['changeIpUrl'],
            "savedByUser": 1
        }
        browser_profile_info['data']['proxy'] = prx
        browser_profile_info['data']['proxyId'] = prx['id']

        prx = {
            "id": info['id'],
            "name": info['name'],
        }
        browser_profile_info_for_start['proxyId'] = prx['id']
        browser_profile_info_for_start['proxy'] = prx
    elif ('proxy' in changes and changes['proxy'] is None):
        browser_profile_info['data']['proxyId'] = 0
        browser_profile_info['data']['proxy'] = None
        browser_profile_info_for_start['proxyId'] = 0
        try:
            del browser_profile_info_for_start['proxy']
        except:
            pass

    Files.save_to_file(f'browsers/{browser_profile_id}/info.json', browser_profile_info)
    Files.save_to_file(f'browsers/{browser_profile_id}/info_for_start.json', browser_profile_info_for_start)

    return browser_profile_info
