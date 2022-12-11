import asyncio
import os
from grafana_backup.dashboardApi import get_dashboard_versions, get_version
from grafana_backup.save_dashboards import get_all_dashboards_in_grafana
from grafana_backup.commons import print_horizontal_line, save_json, to_python2_and_3_compatible_string


async def main(args, settings):
    backup_dir = settings.get('BACKUP_DIR')
    timestamp = settings.get('TIMESTAMP')
    grafana_url = settings.get('GRAFANA_URL')
    http_get_headers = settings.get('HTTP_GET_HEADERS')
    verify_ssl = settings.get('VERIFY_SSL')
    client_cert = settings.get('CLIENT_CERT')
    debug = settings.get('DEBUG')
    pretty_print = settings.get('PRETTY_PRINT')
    uid_support = settings.get('DASHBOARD_UID_SUPPORT')
    session = settings.get('session')

    folder_path = '{0}/dashboard_versions/{1}'.format(backup_dir, timestamp)
    log_file = 'dashboard_versions_{0}.txt'.format(timestamp)

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    await save_dashboard_versions(folder_path, log_file, grafana_url, http_get_headers, verify_ssl, client_cert, debug, pretty_print, uid_support, session)


async def save_dashboard_versions(folder_path, log_file, grafana_url, http_get_headers, verify_ssl, client_cert, debug, pretty_print, uid_support, session):
    limit = 5000
    current_page = 1

    all_dashboards = []
    while True:
        dashboards = await get_all_dashboards_in_grafana(current_page, limit, grafana_url, http_get_headers, verify_ssl, client_cert, debug, session)
        print_horizontal_line()
        if len(dashboards) == 0:
            break
        else:
            current_page += 1
            all_dashboards.extend(dashboards)
    await get_versions_and_save(all_dashboards, folder_path, log_file, grafana_url, http_get_headers, verify_ssl, client_cert, debug, pretty_print, uid_support, session)
    print_horizontal_line()


async def get_versions_and_save(dashboards, folder_path, log_file, grafana_url, http_get_headers, verify_ssl, client_cert, debug, pretty_print, uid_support, session):
    if dashboards:
        tasks = []
        for board in dashboards:
            tasks.append(get_dashboard_versions(board['id'], grafana_url, http_get_headers, verify_ssl, client_cert, debug, session))
        responses = await asyncio.gather(*tasks)
        tasks = []
        for board in dashboards:
            board_folder_path = os.path.join(folder_path, board['uid'])
            if not os.path.exists(board_folder_path):
                os.makedirs(board_folder_path)

            for status, content in responses:
                if status != 200:
                    continue
                if content[0]['dashboardId'] != board['id']:
                    continue
                print("found {0} versions for dashboard {1}".format(len(content), to_python2_and_3_compatible_string(board['title'])))
                tasks.append(get_individual_versions(content, board_folder_path, log_file, grafana_url, http_get_headers, verify_ssl, client_cert, debug, pretty_print, session))
        await asyncio.gather(*tasks)


async def get_individual_versions(versions, folder_path, log_file, grafana_url, http_get_headers, verify_ssl, client_cert, debug, pretty_print, session):
    file_path = folder_path + '/' + log_file
    if versions:
        with open(u"{0}".format(file_path), 'w') as f:
            for version in versions:
                (status, content) = await get_version(version['dashboardId'], version['version'], grafana_url, http_get_headers, verify_ssl, client_cert, debug, session)
                if status == 200:
                    await save_version(str(version['version']), content, folder_path, pretty_print)
                    f.write('{0}\n'.format(version['version']))


async def save_version(file_name, version, folder_path, pretty_print):
    file_path = await save_json(file_name, version, folder_path, 'version', pretty_print)
    print("version: {0} -> saved to: {1}".format(file_name, file_path))
