import re
import ujson as json
import requests
import sys

import ujson

from grafana_backup.commons import log_response, to_python2_and_3_compatible_string


async def health_check(grafana_url, http_get_headers, verify_ssl, client_cert, debug, session):
    url = '{0}/api/health'.format(grafana_url)
    print("\n[Pre-Check] grafana health check: {0}".format(url, session))
    return await send_grafana_get(url, http_get_headers, verify_ssl, client_cert, debug, session)


async def auth_check(grafana_url, http_get_headers, verify_ssl, client_cert, debug, session):
    url = '{0}/api/auth/keys'.format(grafana_url)
    print("\n[Pre-Check] grafana auth check: {0}".format(url, session))
    return await send_grafana_get(url, http_get_headers, verify_ssl, client_cert, debug, session)


async def uid_feature_check(grafana_url, http_get_headers, verify_ssl, client_cert, debug, session):
    # Get first dashboard on first page
    print("\n[Pre-Check] grafana uid feature check: calling 'search_dashboard'")
    (status, content) = await search_dashboard(1, 1, grafana_url, http_get_headers, verify_ssl, client_cert, debug,
                                               session)
    if status == 200 and len(content):
        content = content
        if 'uid' in content[0]:
            dashboard_uid_support = True
        else:
            dashboard_uid_support = False
    else:
        if len(content):
            dashboard_uid_support = "get dashboards failed, status: {0}, msg: {1}".format(status, content)
        else:
            # No dashboards exist, disable uid feature
            dashboard_uid_support = False
    # Get first datasource
    print("\n[Pre-Check] grafana uid feature check: calling 'search_datasource'")
    (status, content) = await search_datasource(grafana_url, http_get_headers, verify_ssl, client_cert, debug, session)
    if status == 200 and len(content):
        if 'uid' in content[0]:
            datasource_uid_support = True
        else:
            datasource_uid_support = False
    else:
        if len(content):
            datasource_uid_support = "get datasources failed, status: {0}, msg: {1}".format(status, content)
        else:
            # No datasources exist, disable uid feature
            datasource_uid_support = False

    return dashboard_uid_support, datasource_uid_support


async def paging_feature_check(grafana_url, http_get_headers, verify_ssl, client_cert, debug, session):
    print("\n[Pre-Check] grafana paging_feature_check: calling 'search_dashboard'")

    async def get_first_dashboard_by_page(page, session):
        (status, content) = await search_dashboard(page, 1, grafana_url, http_get_headers, verify_ssl, client_cert, debug, session)
        if status == 200 and len(content):
            if sys.version_info[0] > 2:
                content[0] = {k: to_python2_and_3_compatible_string(v) for k, v in content[0].items()}
                dashboard_values = sorted(content[0].items(), key=lambda kv: str(kv[1]))
            else:
                content[0] = {k: to_python2_and_3_compatible_string(unicode(v)) for k, v in content[0].iteritems()}
                dashboard_values = sorted(content[0].iteritems(), key=lambda kv: str(kv[1]))
            return True, dashboard_values
        else:
            if len(content):
                return False, "get dashboards failed, status: {0}, msg: {1}".format(status, content)
            else:
                # No dashboards exist, disable paging feature
                return False, False

    # Get first dashboard on first page
    (status, content) = await get_first_dashboard_by_page(1, session)
    if status is False and content is False:
        return False  # Paging feature not supported
    elif status is True:
        dashboard_one_values = content
    else:
        return content  # Fail Message

    # Get second dashboard on second page
    (status, content) = await get_first_dashboard_by_page(2, session)
    if status is False and content is False:
        return False  # Paging feature not supported
    elif status is True:
        dashboard_two_values = content
    else:
        return content  # Fail Message

    # Compare both pages
    return dashboard_one_values != dashboard_two_values


async def search_dashboard(page, limit, grafana_url, http_get_headers, verify_ssl, client_cert, debug, session):
    url = '{0}/api/search/?type=dash-db&limit={1}&page={2}'.format(grafana_url, limit, page)
    print("search dashboard in grafana: {0}".format(url))
    return await send_grafana_get(url, http_get_headers, verify_ssl, client_cert, debug, session)


async def get_dashboard(board_uri, grafana_url, http_get_headers, verify_ssl, client_cert, debug, session):
    url = '{0}/api/dashboards/{1}'.format(grafana_url, board_uri)
    print("query dashboard uri: {0}".format(url))
    (status_code, content) = await send_grafana_get(url, http_get_headers, verify_ssl, client_cert, debug, session)
    return (status_code, content)


async def search_annotations(grafana_url, ts_from, ts_to, http_get_headers, verify_ssl, client_cert, debug, session):
    # there is two types of annotations
    # annotation: are user created, custom ones and can be managed via the api
    # alert: are created by Grafana itself, can NOT be managed by the api
    url = '{0}/api/annotations?type=annotation&limit=5000&from={1}&to={2}'.format(grafana_url, ts_from, ts_to)
    (status_code, content) = await send_grafana_get(url, http_get_headers, verify_ssl, client_cert, debug, session)
    return (status_code, content)


def create_annotation(annotation, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/annotations'.format(grafana_url)
    return send_grafana_post(url, annotation, http_post_headers, verify_ssl, client_cert, debug)


def delete_annotation(id_, grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    r = requests.delete('{0}/api/annotations/{1}'.format(grafana_url, id_), headers=http_get_headers)
    return int(r.status_code)


async def search_alert_channels(grafana_url, http_get_headers, verify_ssl, client_cert, debug, session):
    url = '{0}/api/alert-notifications'.format(grafana_url)
    print("search alert channels in grafana: {0}".format(url, session))
    return await send_grafana_get(url, http_get_headers, verify_ssl, client_cert, debug, session)


def create_alert_channel(payload, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_post('{0}/api/alert-notifications'.format(grafana_url), payload, http_post_headers, verify_ssl,
                             client_cert, debug)


def delete_alert_channel_by_uid(uid, grafana_url, http_post_headers):
    r = requests.delete('{0}/api/alert-notifications/uid/{1}'.format(grafana_url, uid), headers=http_post_headers)
    return int(r.status_code)


def delete_alert_channel_by_id(id_, grafana_url, http_post_headers):
    r = requests.delete('{0}/api/alert-notifications/{1}'.format(grafana_url, id_), headers=http_post_headers)
    return int(r.status_code)


async def search_alerts(grafana_url, http_get_headers, verify_ssl, client_cert, debug, session):
    url = '{0}/api/alerts'.format(grafana_url)
    (status_code, content) = await send_grafana_get(url, http_get_headers, verify_ssl, client_cert, debug, session)
    return (status_code, content)


def pause_alert(id_, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/alerts/{1}/pause'.format(grafana_url, id_)
    payload = '{ "paused": true }'
    (status_code, content) = send_grafana_post(url, payload, http_post_headers, verify_ssl, client_cert, debug)
    return (status_code, content)


def unpause_alert(id_, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/alerts/{1}/pause'.format(grafana_url, id_)
    payload = '{ "paused": false }'
    (status_code, content) = send_grafana_post(url, payload, http_post_headers, verify_ssl, client_cert, debug)
    return (status_code, content)


def delete_folder(uid, grafana_url, http_post_headers):
    r = requests.delete('{0}/api/folders/{1}'.format(grafana_url, uid), headers=http_post_headers)
    return int(r.status_code)


def delete_snapshot(key, grafana_url, http_post_headers):
    r = requests.delete('{0}/api/snapshots/{1}'.format(grafana_url, key), headers=http_post_headers)
    return int(r.status_code)


def delete_dashboard_by_uid(uid, grafana_url, http_post_headers):
    r = requests.delete('{0}/api/dashboards/uid/{1}'.format(grafana_url, uid), headers=http_post_headers)
    return int(r.status_code)


def delete_dashboard_by_slug(slug, grafana_url, http_post_headers):
    r = requests.delete('{0}/api/dashboards/db/{1}'.format(grafana_url, slug), headers=http_post_headers)
    return int(r.status_code)


def create_dashboard(payload, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_post('{0}/api/dashboards/db'.format(grafana_url), payload, http_post_headers, verify_ssl,
                             client_cert, debug)


async def search_datasource(grafana_url, http_get_headers, verify_ssl, client_cert, debug, session):
    print("search datasources in grafana:, session")
    return await send_grafana_get('{0}/api/datasources'.format(grafana_url), http_get_headers, verify_ssl, client_cert,
                                  debug, session)


async def search_snapshot(grafana_url, http_get_headers, verify_ssl, client_cert, debug, session):
    print("search snapshots in grafana:, session")
    return await send_grafana_get('{0}/api/dashboard/snapshots'.format(grafana_url), http_get_headers, verify_ssl,
                            client_cert, debug, session)


async def get_snapshot(key, grafana_url, http_get_headers, verify_ssl, client_cert, debug, session):
    url = '{0}/api/snapshots/{1}'.format(grafana_url, key)
    (status_code, content) = await send_grafana_get(url, http_get_headers, verify_ssl, client_cert, debug, session)
    return (status_code, content)


def create_snapshot(payload, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_post('{0}/api/snapshots'.format(grafana_url), payload, http_post_headers, verify_ssl,
                             client_cert, debug)


def create_datasource(payload, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_post('{0}/api/datasources'.format(grafana_url), payload, http_post_headers, verify_ssl,
                             client_cert, debug)


def delete_datasource_by_uid(uid, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/datasources/uid/{1}'.format(grafana_url, uid)
    r = requests.delete(url, headers=http_post_headers)
    return int(r.status_code)


def delete_datasource_by_id(id_, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/datasources/{1}'.format(grafana_url, id_)
    r = requests.delete(url, headers=http_post_headers)
    return int(r.status_code)


async def search_folders(grafana_url, http_get_headers, verify_ssl, client_cert, debug, session):
    print("search folder in grafana:, session")
    return await send_grafana_get('{0}/api/search/?type=dash-folder'.format(grafana_url), http_get_headers, verify_ssl,
                            client_cert, debug, session)


async def get_folder(uid, grafana_url, http_get_headers, verify_ssl, client_cert, debug, session):
    (status_code, content) = await send_grafana_get('{0}/api/folders/{1}'.format(grafana_url, uid), http_get_headers,
                                              verify_ssl, client_cert, debug, session)
    print("query folder:{0}, status:{1}".format(uid, status_code))
    return (status_code, content)


async def get_folder_permissions(uid, grafana_url, http_get_headers, verify_ssl, client_cert, debug, session):
    (status_code, content) = await send_grafana_get('{0}/api/folders/{1}/permissions'.format(grafana_url, uid),
                                              http_get_headers,
                                              verify_ssl, client_cert, debug, session)
    print("query folder permissions:{0}, status:{1}".format(uid, status_code))
    return (status_code, content)


def update_folder_permissions(payload, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    items = json.dumps({'items': payload})
    return send_grafana_post('{0}/api/folders/{1}/permissions'.format(grafana_url, payload[0]['uid']), items,
                             http_post_headers, verify_ssl, client_cert,
                             debug)


async def get_folder_id(dashboard, grafana_url, http_post_headers, verify_ssl, client_cert, debug, session):
    folder_uid = ""
    try:
        folder_uid = dashboard['meta']['folderUid']
    except (KeyError):
        matches = re.search('dashboards\/f\/(.*)\/.*', dashboard['meta']['folderUrl'])
        if matches is not None:
            folder_uid = matches.group(1)
        else:
            folder_uid = '0'

    if (folder_uid != ""):
        print("debug: quering with uid {}".format(folder_uid))
        response = await get_folder(folder_uid, grafana_url, http_post_headers, verify_ssl, client_cert, debug, session)
        if isinstance(response[1], dict):
            folder_data = response[1]
        else:
            folder_data = json.loads(response[1])

        try:
            return folder_data['id']
        except (KeyError):
            return 0
    else:
        return 0


def create_folder(payload, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_post('{0}/api/folders'.format(grafana_url), payload, http_post_headers, verify_ssl, client_cert,
                             debug)


async def get_dashboard_versions(dashboard_id, grafana_url, http_get_headers, verify_ssl, client_cert, debug, session):
    (status_code, content) = await send_grafana_get('{0}/api/dashboards/id/{1}/versions'.format(grafana_url, dashboard_id, session),
                                              http_get_headers,
                                              verify_ssl, client_cert, debug, session)
    print("query dashboard versions: {0}, status: {1}".format(dashboard_id, status_code))
    return (status_code, content)


async def get_version(dashboard_id, version_number, grafana_url, http_get_headers, verify_ssl, client_cert, debug, session):
    (status_code, content) = await send_grafana_get(
        '{0}/api/dashboards/id/{1}/versions/{2}'.format(grafana_url, dashboard_id, version_number), http_get_headers,
        verify_ssl, client_cert, debug, session)
    print("query dashboard {0} version {1}, status: {2}".format(dashboard_id, version_number, status_code))
    return (status_code, content)


async def search_orgs(grafana_url, http_get_headers, verify_ssl, client_cert, debug, session):
    return await send_grafana_get('{0}/api/orgs'.format(grafana_url), http_get_headers, verify_ssl,
                            client_cert, debug, session)


async def get_org(id, grafana_url, http_get_headers, session, verify_ssl=False, client_cert=None, debug=True):
    return await send_grafana_get('{0}/api/orgs/{1}'.format(grafana_url, id),
                            http_get_headers, verify_ssl, client_cert, debug, session)


def create_org(payload, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_post('{0}/api/orgs'.format(grafana_url), payload, http_post_headers, verify_ssl, client_cert,
                             debug)


def update_org(id, payload, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_put('{0}/api/orgs/{1}'.format(grafana_url, id), payload, http_post_headers, verify_ssl,
                            client_cert,
                            debug)


async def search_users(page, limit, grafana_url, http_get_headers, verify_ssl, client_cert, debug, session):
    return await send_grafana_get('{0}/api/users?perpage={1}&page={2}'.format(grafana_url, limit, page),
                            http_get_headers, verify_ssl, client_cert, debug, session)


async def get_users(grafana_url, http_get_headers, verify_ssl, client_cert, debug, session):
    return await send_grafana_get('{0}/api/org/users'.format(grafana_url), http_get_headers, verify_ssl, client_cert, debug, session)


def set_user_role(user_id, role, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    json_payload = json.dumps({'role': role})
    url = '{0}/api/org/users/{1}'.format(grafana_url, user_id)
    r = requests.patch(url, headers=http_post_headers, data=json_payload, verify=verify_ssl, cert=client_cert)
    return (r.status_code, r.json())


async def get_user(id, grafana_url, http_get_headers, session, verify_ssl=False, client_cert=None, debug=True):
    status, content = await send_grafana_get('{0}/api/users/{1}'.format(grafana_url, id),
                            http_get_headers, verify_ssl, client_cert, debug, session)
    if status == 200:
        status, user_org_content = await get_user_org(content['id'], grafana_url, http_get_headers, session, verify_ssl, client_cert, debug)
        if status == 200:
            content.update({'orgs': user_org_content})
    return status, content


async def get_user_org(id, grafana_url, http_get_headers, session, verify_ssl=False, client_cert=None, debug=True):
    return await send_grafana_get('{0}/api/users/{1}/orgs'.format(grafana_url, id),
                            http_get_headers, verify_ssl, client_cert, debug, session)


def create_user(payload, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_post('{0}/api/admin/users'.format(grafana_url), payload, http_post_headers, verify_ssl,
                             client_cert,
                             debug)


def add_user_to_org(org_id, payload, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_post('{0}/api/orgs/{1}/users'.format(grafana_url, org_id), payload, http_post_headers,
                             verify_ssl, client_cert,
                             debug)


async def send_grafana_get(url, http_get_headers, verify_ssl, client_cert, debug, session):
    async with session.get(url, headers=http_get_headers) as r:
        r.status_code = r.status
        if debug:
            class Resp:
                status_code = ""
                text = ""
                _json = ""

                def json(self):
                    return self._json
            resp = Resp()
            resp.status_code = r.status_code
            resp.text = await r.text()
            resp._json = await r.json()
            log_response(resp)
        return r.status_code, await r.json()


def send_grafana_post(url, json_payload, http_post_headers, verify_ssl=False, client_cert=None, debug=True):
    r = requests.post(url, headers=http_post_headers, data=json_payload, verify=verify_ssl, cert=client_cert)
    if debug:
        log_response(r)
    try:
        return (r.status_code, r.json())
    except ValueError:
        return (r.status_code, r.text)


def send_grafana_put(url, json_payload, http_post_headers, verify_ssl=False, client_cert=None, debug=True):
    r = requests.put(url, headers=http_post_headers, data=json_payload, verify=verify_ssl, cert=client_cert)
    if debug:
        log_response(r)
    return (r.status_code, r.json())
