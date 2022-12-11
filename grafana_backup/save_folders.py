import asyncio
import os
import ujson as json

import aiofiles

from grafana_backup.dashboardApi import search_folders, get_folder, get_folder_permissions
from grafana_backup.commons import to_python2_and_3_compatible_string, print_horizontal_line, save_json


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

    folder_path = '{0}/folders/{1}'.format(backup_dir, timestamp)
    log_file = 'folders_{0}.txt'.format(timestamp)

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    folders = await get_all_folders_in_grafana(grafana_url, http_get_headers, verify_ssl, client_cert, debug, session)
    print_horizontal_line()
    await get_individual_folder_setting_and_save(folders, folder_path, log_file, grafana_url, http_get_headers, verify_ssl, client_cert, debug, pretty_print, uid_support, session)
    print_horizontal_line()


async def get_all_folders_in_grafana(grafana_url, http_get_headers, verify_ssl, client_cert, debug, session):
    status_code, content = await search_folders(grafana_url, http_get_headers, verify_ssl, client_cert, debug, session)
    status = status_code
    if status == 200:
        folders = content
        print("There are {0} folders:".format(len(content)))
        for folder in folders:
            print("name: {0}".format(to_python2_and_3_compatible_string(folder['title'])))
        return folders
    else:
        print("get folders failed, status: {0}, msg: {1}".format(status, content))
        return []


async def save_folder_setting(folder_name, file_name, folder_settings, folder_permissions, folder_path, pretty_print):
    file_path = await save_json(file_name, folder_settings, folder_path, 'folder', pretty_print)
    print("folder:{0} are saved to {1}".format(folder_name, file_path))
    # NOTICE: The 'folder_permission' file extension had the 's' removed to work with the magical dict logic in restore.py...
    file_path = await save_json(file_name,  folder_permissions, folder_path, 'folder_permission', pretty_print)
    print("folder permissions:{0} are saved to {1}".format(folder_name, file_path))


async def get_individual_folder_setting_and_save(folders, folder_path, log_file, grafana_url, http_get_headers, verify_ssl, client_cert, debug, pretty_print, uid_support, session):
    file_path = folder_path + '/' + log_file
    async with aiofiles.open(u"{0}".format(file_path), 'w+') as f:
        tasks_folder_settings = []
        tasks_folder_permissions = []
        for folder in folders:
            tasks_folder_settings.append(get_folder(folder['uid'], grafana_url, http_get_headers, verify_ssl, client_cert, debug, session))
            tasks_folder_permissions.append(get_folder_permissions(folder['uid'], grafana_url, http_get_headers, verify_ssl, client_cert, debug, session))

        responses_folder_settings = await asyncio.gather(*tasks_folder_settings)
        responses_folder_permissions = await asyncio.gather(*tasks_folder_permissions)

        for status_folder_settings, content_folder_settings in responses_folder_settings:
            for status_folder_permissions, content_folder_permissions in responses_folder_permissions:
                if isinstance(content_folder_permissions, list):
                    if content_folder_settings['uid'] != content_folder_permissions[0]['uid']:
                        continue
                elif content_folder_settings['uid'] != content_folder_permissions['uid']:
                    continue
                if uid_support:
                    folder_uri = "uid/{0}".format(content_folder_settings['uid'])
                else:
                    folder_uri = content_folder_settings['uri']
                if status_folder_settings == 200 and status_folder_permissions == 200:
                    await save_folder_setting(
                        to_python2_and_3_compatible_string(folder['title']),
                        folder_uri,
                        content_folder_settings,
                        content_folder_permissions,
                        folder_path,
                        pretty_print
                    )
                    await f.write('{0}\t{1}\n'.format(folder_uri, to_python2_and_3_compatible_string(folder['title'])))
