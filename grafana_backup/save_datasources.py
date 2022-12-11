import ujson as json
import os
from grafana_backup.dashboardApi import search_datasource
from grafana_backup.commons import print_horizontal_line, save_json


async def main(args, settings):
    backup_dir = settings.get('BACKUP_DIR')
    timestamp = settings.get('TIMESTAMP')
    grafana_url = settings.get('GRAFANA_URL')
    http_get_headers = settings.get('HTTP_GET_HEADERS')
    verify_ssl = settings.get('VERIFY_SSL')
    client_cert = settings.get('CLIENT_CERT')
    debug = settings.get('DEBUG')
    pretty_print = settings.get('PRETTY_PRINT')
    uid_support = settings.get('DATASOURCE_UID_SUPPORT')
    session = settings.get('session')

    folder_path = '{0}/datasources/{1}'.format(backup_dir, timestamp)

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    await get_all_datasources_and_save(folder_path, grafana_url, http_get_headers, verify_ssl, client_cert, debug, pretty_print, uid_support, session)
    print_horizontal_line()


async def save_datasource(file_name, datasource_setting, folder_path, pretty_print):
    file_path = await save_json(file_name, datasource_setting, folder_path, 'datasource', pretty_print)
    print("datasource:{0} is saved to {1}".format(file_name, file_path))


async def get_all_datasources_and_save(folder_path, grafana_url, http_get_headers, verify_ssl, client_cert, debug, pretty_print, uid_support, session):
    status_code, content = await search_datasource(grafana_url, http_get_headers, verify_ssl, client_cert, debug, session)
    if status_code == 200:
        datasources = content
        print("There are {0} datasources:".format(len(datasources)))
        for datasource in datasources:
            if debug:
                print(datasource)
            if uid_support:
                datasource_name = datasource['uid']
            else:
                datasource_name = datasource['name']
            await save_datasource(datasource_name, datasource, folder_path, pretty_print)
    else:
        print("query datasource failed, status: {0}, msg: {1}".format(status_code, content))
