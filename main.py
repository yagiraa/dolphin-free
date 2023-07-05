import os
import shutil
import math
from pathlib import Path

from flask import Flask
from flask import request
from flask import send_file

from modules.files import Files
from utils import *
from config import *

FIRST_TIME_RUNNING = False

app = Flask(__name__)


@app.route('/browser_profiles/<int:browser_profile_id>', methods=['GET', 'PATCH'])
def get_profile(browser_profile_id):
    if (request.method == 'GET'):
        if (os.path.exists(os.path.join(os.getcwd(), 'browsers', str(browser_profile_id), 'info.json')) == False):
            resp = send_request(
                method='GET',
                url=REMOTE_API_BASE_URL + request.full_path,
                headers=request.headers,
            )

            Files.save_to_file(f'browsers/{browser_profile_id}/info.json', resp.json())

        browser_profile_info = Files.read_from_file(f'browsers/{browser_profile_id}/info.json')

        return browser_profile_info
    else:
        browser_profile_info = change_browser_config(request.json, browser_profile_id, request)

        return browser_profile_info


@app.route('/browser_profiles/<method>')
def browser_profiles_additional_methods(method):
    if (method == 'available'):
        profiles = get_path_files(os.path.join(os.getcwd(), 'browsers'))
        available = Files.read_from_file('jsons/available.json')
        available['data']['ids'] = [int(i) for i in profiles]

        return available
    elif (method == 'statuses'):
        profile_statuses = Files.read_from_file('jsons/profile_statuses.json')

        return profile_statuses
    elif (method == 'tags'):
        profile_tags = Files.read_from_file('jsons/profile_tags.json')

        return profile_tags


@app.route('/')
def sync_methods():
    action = request.args.get('actionType')

    if (action == 'getDatadirHash'):
        dirhash = Files.read_from_file('jsons/dirhash.json')

        return dirhash
    elif (action == 'getDatadir'):
        browser_profile_id = request.args.get('browserProfileId')
        if (os.path.exists(os.path.join(os.getcwd(), 'browsers', str(browser_profile_id), f'{browser_profile_id}.datadir.zip')) == False):
            browser_profile_not_found = Files.read_from_file('jsons/browser_profile_not_found.json')

            return browser_profile_not_found

        download = Files.read_from_file('jsons/download_link.json')
        download['data']['link'] = f'{LOCAL_API_BASE_URL}/download_datadir/{browser_profile_id}'
        download['data']['links']['aws'] = f'{LOCAL_API_BASE_URL}/download_datadir/{browser_profile_id}'
        download['browserProfileId'] = browser_profile_id

        return download
    

@app.route('/download_datadir/<browser_profile_id>')
def upload_archive(browser_profile_id):
    file_path = f'browsers/{browser_profile_id}/{browser_profile_id}.datadir.zip'

    return send_file(file_path, as_attachment=True)


@app.route('/browser_profiles/<browser_profile_id>/<method>', methods=['GET', 'POST'])
def browser_profile_launch_methods(browser_profile_id, method):
    global FIRST_TIME_RUNNING

    if (method == 'canUpdate'):
        result = Files.read_from_file('jsons/result.json')

        return result
    elif (method == 'events'):
        if (request.json['type'] == 'stop'):
            if (FIRST_TIME_RUNNING == True):
                resp = send_request(
                    method='DELETE',
                    url=REMOTE_API_BASE_URL + '/browser_profiles',
                    headers=request.headers,
                    payload={"ids": [browser_profile_id]},
                )

                logger.success(f'Успешно удалил профиль #{browser_profile_id} с серверов')
                FIRST_TIME_RUNNING = False

            do_backup(browser_profile_id)
            result = Files.read_from_file('jsons/event_stop.json')
        else:
            result = Files.read_from_file('jsons/event_start.json')
        result['data']['browserProfileId'] = int(browser_profile_id)

        return result


@app.route('/index.php', methods=['POST'])
def download_archive():
    action = request.args.get('actionType')

    if (action == 'importDatadir'):
        browser_profile_id = request.args.get('browserProfileId')
        run_id = request.args.get('runId')
        archive = request.files['file']
        archive.save(f'browsers/{browser_profile_id}/{browser_profile_id}.datadir.zip')

        successfull_upload = Files.read_from_file('jsons/successfull_upload.json')
        successfull_upload['browserProfileId'] = browser_profile_id

        return successfull_upload


@app.route('/browser_profiles', methods=['GET', 'POST', 'DELETE'])
@check_token_expire
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

        all_profiles = Files.read_from_file('jsons/all_profiles.json')

        first_profile = (settings['page'] - 1) * settings['limit']
        last_profile = len(profiles) if (settings['page'] * settings['limit'] > len(profiles)) else settings['page'] * settings['limit']

        for i in profiles[first_profile:last_profile]:
            profile_info = Files.read_from_file(f'browsers/{i}/info_for_start.json')
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
        resp = send_request(
            method='POST',
            url=REMOTE_API_BASE_URL + request.full_path,
            headers=request.headers,
            payload=request.json,
        )
        
        return_value = resp.text

        browser_profile_id = resp.json()['browserProfileId']

        Path(os.path.join(os.getcwd(), 'browsers', str(browser_profile_id))).mkdir(parents=True, exist_ok=True)
        
        resp = send_request(
            method='GET',
            url=REMOTE_API_BASE_URL + '/browser_profiles',
            headers={'Authorization': request.headers['Authorization']},
        )
        
        for i in resp.json()['data']:
            if (i['id'] == browser_profile_id):
                Files.save_to_file(f'browsers/{browser_profile_id}/info_for_start.json', i)
                break

        resp = send_request(
            method='GET',
            url=f'http://localhost:3001/v1.0/browser_profiles/{browser_profile_id}/start',
        )
        
        logger.success(f'Успешно создался профиль #{browser_profile_id} | Запускаю!')

        FIRST_TIME_RUNNING = True

        return return_value
    elif (request.method == 'DELETE'):
        for i in request.json['ids']:
            shutil.rmtree(os.path.join(os.getcwd(), 'browsers', str(i)))
            try:
                shutil.move(os.path.join(os.getcwd(), 'browsers_backup', str(i)), os.path.join(os.getcwd(), 'browsers_backup', str(i) + ' (deleted)'))
            except:
                pass
        return {}


@app.route('/profile')
@check_token_expire
def profile():
    profile_info = Files.read_from_file('jsons/profile.json')

    profiles = get_path_files(os.path.join(os.getcwd(), 'browsers'))
    profile_info['data']['subscription']['browserProfiles']['count'] = len(profiles)

    return profile_info


@app.route('/subscription')
@check_token_expire
def subscription():
    subscription_info = Files.read_from_file('jsons/subscription.json')

    profiles = get_path_files(os.path.join(os.getcwd(), 'browsers'))
    subscription_info['data']['browserProfiles']['count'] = len(profiles)

    return subscription_info



@app.route('/team/users')
@check_token_expire
def team():
    team = Files.read_from_file('jsons/team.json')

    return team


@app.route('/settings', methods=['GET', 'POST', 'DELETE', 'PATCH'])
@check_token_expire
def settings():
    settings = Files.read_from_file('jsons/settings.json')

    return settings


@app.route('/onbr')
@check_token_expire
def onbr():
    onbr = Files.read_from_file('jsons/onbr.json')

    return onbr


@app.route('/restriction')
@check_token_expire
def restriction():
    restriction = Files.read_from_file('jsons/restriction.json')

    return restriction


@app.route('/dolphin-anty/anty-connect/releases/download/<local_api_id>/<file>', methods=['GET', 'POST', 'HEAD'])
def download_local_api(local_api_id, file):
    file_path = f'files/{file}'

    return send_file(file_path, as_attachment=True)


@app.route('/auth/refreshToken', methods=['GET', 'POST', 'DELETE', 'PATCH'])
def refresh_token(info=None):
    resp = send_request(
        method=request.method,
        url=REMOTE_API_BASE_URL + request.full_path,
        headers=request.headers,
        payload={} if request.method == 'GET' else request.json,
    )

    return resp.text


@app.route('/branches')
def check_local_api():
    local_api_info = Files.read_from_file('jsons/local_api_info.json')

    return local_api_info


@app.route('/proxy', methods=['GET', 'POST', 'DELETE', 'PATCH'])
@app.route('/proxy/<info>/last_check', methods=['GET', 'POST', 'DELETE', 'PATCH'])
@app.route('/extensions', methods=['GET', 'POST', 'DELETE', 'PATCH'])
@app.route('/scripts', methods=['GET', 'POST', 'DELETE', 'PATCH'])
@app.route('/scripts/<info>', methods=['GET', 'POST', 'DELETE', 'PATCH'])
@app.route('/fingerprints/<info>', methods=['GET', 'POST', 'DELETE', 'PATCH'])
@app.route('/bookmarks', methods=['GET', 'POST', 'DELETE', 'PATCH'])
@app.route('/bookmarks/<info>', methods=['GET', 'POST', 'DELETE', 'PATCH'])
@check_token_expire
def scripts(info=None):
    resp = send_request(
        method=request.method,
        url=REMOTE_API_BASE_URL + request.full_path,
        headers=request.headers,
        payload={} if request.method == 'GET' else request.json,
    )

    return resp.text


if __name__ == '__main__':
    app.run()