import os
import json
import shutil
import math
import requests
from time import sleep
from pathlib import Path

from flask import Flask
from flask import request
from flask import send_file

app = Flask(__name__)

LOCAL_API_BASE_URL = 'http://127.0.0.1:5000'
REMOTE_API_BASE_URL = 'https://dolphin-anty-api.com'
REMOTE_SYNC_API_BASE_URL = 'https://sync.dolphin-anty-api.com'

FIRST_TIME_RUNNING = False

def get_absolute_path(*args):
    path = os.getcwd()
    for i in args:
        path = os.path.join(path, str(i))
    return path

def sort_profiles(settings, all_profiles):
    def sort_by_notes(d):
        if (d['notes']['content'] is None):
            return '<p></p>'
        return d['notes']['content']

    def sort_by_status(d):
        if ('status' not in d or d['status'] is None):
            return '0'
        return d['status']

    if (settings['sortBy'] == 'name' and settings['order'] == 'DESC'):
        all_profiles['data'].sort(key=lambda d: d['name'], reverse=True)
    elif (settings['sortBy'] == 'name' and settings['order'] == 'ASC'):
        all_profiles['data'].sort(key=lambda d: d['name'])

    elif (settings['sortBy'] == 'status' and settings['order'] == 'DESC'):
        all_profiles['data'].sort(key=sort_by_status, reverse=True)
    elif (settings['sortBy'] == 'status' and settings['order'] == 'ASC'):
        all_profiles['data'].sort(key=sort_by_status)

    elif (settings['sortBy'] == 'notes' and settings['order'] == 'DESC'):
        all_profiles['data'].sort(key=sort_by_notes, reverse=True)
    elif (settings['sortBy'] == 'notes' and settings['order'] == 'ASC'):
        all_profiles['data'].sort(key=sort_by_notes)

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


def get_path_files(path):
    files = os.listdir(path)
    files.remove('dont_delete.txt')
    return files


def change_browser_config(changes, browser_profile_id, request):
    with open(f'browsers/{browser_profile_id}/info.json', 'r') as file:
        browser_profile_info = json.load(file)
    with open(f'browsers/{browser_profile_id}/info_for_start.json', 'r') as file:
        browser_profile_info_for_start = json.load(file)

    browser_profile_info['data'].update(changes)
    browser_profile_info_for_start.update(changes)
    if ('proxy' in changes and changes['proxy'] is not None and 'id' in changes['proxy']):
        resp = requests.get(REMOTE_API_BASE_URL + f"/proxy?ids[0]={changes['proxy']['id']}", headers={'Authorization': request.headers['Authorization']})
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
        resp = requests.post(REMOTE_API_BASE_URL + '/proxy', headers={'Authorization': request.headers['Authorization']}, json=changes['proxy'])
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
        browser_profile_info_for_start['proxyId'] = 0

    with open(f'browsers/{browser_profile_id}/info.json', 'w') as file:
        file.write(json.dumps(browser_profile_info, indent=4))
    with open(f'browsers/{browser_profile_id}/info_for_start.json', 'w') as file:
        file.write(json.dumps(browser_profile_info_for_start, indent=4))

    return browser_profile_info


@app.route('/browser_profiles/<int:browser_profile_id>', methods=['GET', 'PATCH'])
def get_profile(browser_profile_id):
    if (request.method == 'GET'):
        if (os.path.exists(os.path.join(os.getcwd(), 'browsers', str(browser_profile_id), 'info.json')) == False):
            resp = requests.get(REMOTE_API_BASE_URL + request.full_path, headers=request.headers)
            with open(f'browsers/{browser_profile_id}/info.json', 'w') as file:
                file.write(json.dumps(resp.json(), indent=4))

        with open(f'browsers/{browser_profile_id}/info.json', 'r') as file:
            browser_profile_info = json.load(file)

        return browser_profile_info
    else:
        browser_profile_info = change_browser_config(request.json, browser_profile_id, request)
        return browser_profile_info


@app.route('/browser_profiles/<method>')
def browser_profiles_additional_methods(method):
    if (method == 'available'):
        profiles = get_path_files(os.path.join(os.getcwd(), 'browsers'))
        with open('jsons/available.json', 'r') as file:
            available = json.load(file)
        available['data']['ids'] = [int(i) for i in profiles]
        return available
    elif (method == 'statuses'):
        with open(f'jsons/profile_statuses.json', 'r') as file:
            profile_statuses = json.load(file)
        return profile_statuses
    elif (method == 'tags'):
        with open(f'jsons/profile_tags.json', 'r') as file:
            profile_tags = json.load(file)
        return profile_tags


@app.route('/')
def sync_methods():
    action = request.args.get('actionType')

    if (action == 'getDatadirHash'):
        with open('jsons/dirhash.json', 'r') as file:
            dirhash = json.load(file)
        return dirhash
    elif (action == 'getDatadir'):
        browser_profile_id = request.args.get('browserProfileId')
        if (os.path.exists(os.path.join(os.getcwd(), 'browsers', str(browser_profile_id), f'{browser_profile_id}.datadir.zip')) == False):
            with open('jsons/browser_profile_not_found.json', 'r') as file:
                browser_profile_not_found = json.load(file)
            return browser_profile_not_found

        with open('jsons/download_link.json', 'r') as file:
            download = json.load(file)
        download['data']['link'] = f'{LOCAL_API_BASE_URL}/download_datadir/{browser_profile_id}'
        download['data']['links']['aws'] = f'{LOCAL_API_BASE_URL}/download_datadir/{browser_profile_id}'
        download['browserProfileId'] = browser_profile_id
        return download


@app.route('/download_datadir/<browser_profile_id>')
def download_datadir(browser_profile_id):
    zip_path = f'browsers/{browser_profile_id}/{browser_profile_id}.datadir.zip'
    return send_file(zip_path, as_attachment=True)


@app.route('/browser_profiles/<browser_profile_id>/<method>')
def browser_profile_launch_methods(browser_profile_id, method):
    global FIRST_TIME_RUNNING

    if (method == 'mark-as-running'):
        with open('jsons/mark_as_running.json', 'r') as file:
            marked = json.load(file)
        return marked
    elif (method == 'mark-as-stopped'):
        if (FIRST_TIME_RUNNING == True):
            resp = requests.delete(REMOTE_API_BASE_URL + '/browser_profiles', headers={'Authorization': request.headers['Authorization']}, json={"ids": [browser_profile_id]})
            FIRST_TIME_RUNNING = False
        with open('jsons/mark_as_running.json', 'r') as file:
            marked = json.load(file)
        return marked
    elif (method == 'canUpdate'):
        return {'result': True}


@app.route('/index.php', methods=['POST'])
def upload_archive():
    action = request.args.get('actionType')
    if (action == 'importDatadir'):
        browser_profile_id = request.args.get('browserProfileId')
        run_id = request.args.get('runId')
        archive = request.files[f'file']
        archive.save(f'browsers/{browser_profile_id}/{browser_profile_id}.datadir.zip')

        with open('jsons/successfull_upload.json', 'r') as file:
            successfull_upload = json.load(file)
        successfull_upload['browserProfileId'] = browser_profile_id

        return successfull_upload


@app.route('/team/users')
def get_team():
    with open(f'jsons/team.json', 'r') as file:
        team = json.load(file)
    return team


@app.route('/profile')
def profile():
    with open(f'jsons/profile.json', 'r') as file:
        profile_info = json.load(file)

    profiles = get_path_files(os.path.join(os.getcwd(), 'browsers'))
    profile_info['data']['subscription']['browserProfiles']['count'] = len(profiles)
    return profile_info


@app.route('/subscription')
def subscription():
    with open(f'jsons/subscription.json', 'r') as file:
        subscription_info = json.load(file)

    profiles = get_path_files(os.path.join(os.getcwd(), 'browsers'))
    subscription_info['data']['browserProfiles']['count'] = len(profiles)

    return subscription_info


@app.route('/branches')
def check_local_api():
    with open(f'jsons/local_api_info.json', 'r') as file:
        local_api_info = json.load(file)
    return local_api_info


@app.route('/settings')
def settings():
    return {"data": []}


@app.route('/onbr')
def onbr():
    return {"response": {"group": "B","step": "1"}}


@app.route('/restriction')
def restriction():
    return {"restrict": False,"accountCount": 1}


@app.route('/browser_profiles', methods=['GET', 'POST', 'DELETE'])
def browser_profiles():
    global FIRST_TIME_RUNNING

    if (request.method == 'GET'):
        settings = {
                'page': 1,
                'limit': 50,
                }
        settings.update(dict(request.args))
        settings['page'] = int(settings['page'])
        settings['limit'] = int(settings['limit'])

        profiles = get_path_files(os.path.join(os.getcwd(), 'browsers'))

        with open(f'jsons/all_profiles.json', 'r') as file:
            all_profiles = json.load(file)

        first_profile = (settings['page'] - 1) * settings['limit']
        last_profile = len(profiles) if (settings['page'] * settings['limit'] > len(profiles)) else settings['page'] * settings['limit']

        for i in profiles[first_profile:last_profile]:
            with open(f'browsers/{i}/info_for_start.json', 'r') as file:
                profile_info = json.load(file)
            all_profiles['data'].append(profile_info)

        if ('sortBy' in settings):
            sort_profiles(settings, all_profiles)
        if ('query' in settings):
            search_profiles(settings, all_profiles)

        all_profiles['current_page'] = settings['page']
        all_profiles['per_page'] = settings['limit']
        all_profiles['from'] = first_profile + 1
        if (settings['page'] * settings['limit'] > len(profiles)):
            all_profiles['next_page_url'] =  None
        else:
            all_profiles['next_page_url'] = f'http:\/\/127.0.0.1:5000\/browser_profiles?page={settings["page"] + 1}'
        if (settings['page'] == 1):
            all_profiles['prev_page_url'] =  None
        else:
            all_profiles['prev_page_url'] = f'http:\/\/127.0.0.1:5000\/browser_profiles?page={settings["page"] - 1}'
        all_profiles['to'] = last_profile
        all_profiles['last_page'] = math.ceil(len(profiles) / settings['limit'])
        all_profiles['total'] = len(profiles)

        return all_profiles
    elif (request.method == 'POST'):
        resp = requests.post(REMOTE_API_BASE_URL + request.full_path, headers=request.headers, json=request.json)
        if (resp.status_code != 200):
            print(resp.text)
            return
        ret_val = resp.text
        browser_profile_id = resp.json()['browserProfileId']

        Path(os.path.join(os.getcwd(), 'browsers', str(browser_profile_id))).mkdir(parents=True, exist_ok=True)
        resp = requests.get(REMOTE_API_BASE_URL + '/browser_profiles', headers={'Authorization': request.headers['Authorization']})
        for i in resp.json()['data']:
            if (i['id'] == browser_profile_id):
                with open(f'browsers/{browser_profile_id}/info_for_start.json', 'w') as file:
                    file.write(json.dumps(i, indent=4))
                break

        requests.get(f'http://localhost:3001/v1.0/browser_profiles/{browser_profile_id}/start')
        FIRST_TIME_RUNNING = True

        return ret_val
    elif (request.method == 'DELETE'):
        for i in request.json['ids']:
            shutil.rmtree(os.path.join(os.getcwd(), 'browsers', str(i)))

        return {"success": True}


@app.route('/dolphin-anty/anty-connect/releases/download/<local_api_id>/<file>', methods=['GET', 'POST', 'HEAD'])
def download_local_api(local_api_id, file):
    file_path = f'files/{file}'
    return send_file(file_path, as_attachment=True)


@app.route('/proxy', methods=['GET', 'POST', 'DELETE', 'PATCH'])
@app.route('/proxy/<info>/last_check', methods=['GET', 'POST', 'DELETE', 'PATCH'])
@app.route('/extensions', methods=['GET', 'POST', 'DELETE', 'PATCH'])
@app.route('/scripts', methods=['GET', 'POST', 'DELETE', 'PATCH'])
@app.route('/scripts/<info>', methods=['GET', 'POST', 'DELETE', 'PATCH'])
@app.route('/fingerprints/<info>', methods=['GET', 'POST', 'DELETE', 'PATCH'])
@app.route('/bookmarks', methods=['GET', 'POST', 'DELETE', 'PATCH'])
@app.route('/bookmarks/<info>', methods=['GET', 'POST', 'DELETE', 'PATCH'])
def scripts(info=None):
    if (request.method == 'GET'):
        resp = requests.get(REMOTE_API_BASE_URL + request.full_path, headers=request.headers)
        return resp.text
    elif (request.method == 'POST'):
        resp = requests.post(REMOTE_API_BASE_URL + request.full_path, headers=request.headers, json=request.json)
        return resp.text
    elif (request.method == 'DELETE'):
        resp = requests.delete(REMOTE_API_BASE_URL + request.full_path, headers=request.headers, json=request.json)
        return resp.text
    elif (request.method == 'PATCH'):
        resp = requests.patch(REMOTE_API_BASE_URL + request.full_path, headers=request.headers, json=request.json)
        return resp.text


if __name__ == '__main__':
    app.run()
