import asyncio

import ujson as json
import os
import aiofiles

from grafana_backup.dashboardApi import search_dashboard, get_dashboard
from grafana_backup.commons import to_python2_and_3_compatible_string, print_horizontal_line, save_json


async def main(args, settings):
    backup_dir = settings.get('BACKUP_DIR')
    timestamp = settings.get('TIMESTAMP')
    limit = settings.get('SEARCH_API_LIMIT')
    grafana_url = settings.get('GRAFANA_URL')
    http_get_headers = settings.get('HTTP_GET_HEADERS')
    verify_ssl = settings.get('VERIFY_SSL')
    client_cert = settings.get('CLIENT_CERT')
    debug = settings.get('DEBUG')
    pretty_print = settings.get('PRETTY_PRINT')
    uid_support = settings.get('DASHBOARD_UID_SUPPORT')
    paging_support = settings.get('PAGING_SUPPORT')
    session = settings.get('session')

    folder_path = '{0}/dashboards/{1}'.format(backup_dir, timestamp)
    log_file = 'dashboards_{0}.txt'.format(timestamp)

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    if paging_support:
        await save_dashboards_above_Ver6_2(folder_path, log_file, grafana_url, http_get_headers, verify_ssl,
                                           client_cert, debug, pretty_print, uid_support, session)
    else:
        await save_dashboards(folder_path, log_file, limit, grafana_url, http_get_headers, verify_ssl, client_cert,
                              debug, pretty_print, uid_support, session)


async def get_all_dashboards_in_grafana(page, limit, grafana_url, http_get_headers, verify_ssl, client_cert, debug,
                                        session):
    (status, content) = await search_dashboard(page,
                                               limit,
                                               grafana_url,
                                               http_get_headers,
                                               verify_ssl, client_cert,
                                               debug, session)
    if status == 200:
        dashboards = content
        print("There are {0} dashboards:".format(len(dashboards)))
        for board in dashboards:
            print('name: {0}'.format(to_python2_and_3_compatible_string(board['title'])))
        return dashboards
    else:
        print("get dashboards failed, status: {0}, msg: {1}".format(status, content))
        return []


async def save_dashboard_setting(dashboard_name, file_name, dashboard_settings, folder_path, pretty_print):
    file_path = await save_json(file_name, dashboard_settings, folder_path, 'dashboard', pretty_print)
    print("dashboard: {0} -> saved to: {1}".format(dashboard_name, file_path))


async def get_individual_dashboard_setting_and_save(dashboards, folder_path, log_file, grafana_url, http_get_headers,
                                                    verify_ssl, client_cert, debug, pretty_print, uid_support, session):
    file_path = folder_path + '/' + log_file
    if dashboards:
        tasks = []
        for board in dashboards:
            if uid_support:
                board_uri = "uid/{0}".format(board['uid'])
            else:
                board_uri = board['uri']

            tasks.append(asyncio.ensure_future(get_dashboard(board_uri, grafana_url, http_get_headers, verify_ssl,
                                                             client_cert, debug, session)))
        responses = await asyncio.gather(*tasks)

        async with aiofiles.open(u"{0}".format(file_path), 'w') as f:
            for status, board in responses:
                board_uri = "uid/{0}".format(board['dashboard']['uid'])

                if status == 200:
                    await save_dashboard_setting(
                        to_python2_and_3_compatible_string(board['dashboard']['title']),
                        board_uri,
                        board,
                        folder_path,
                        pretty_print
                    )
                    await f.write('{0}\t{1}\n'.format(board_uri, to_python2_and_3_compatible_string(board['dashboard']['title'])))


async def save_dashboards_above_Ver6_2(folder_path, log_file, grafana_url, http_get_headers, verify_ssl, client_cert,
                                       debug, pretty_print, uid_support, session):
    limit = 5000  # limit is 5000 above V6.2+
    current_page = 1
    while True:
        dashboards = await get_all_dashboards_in_grafana(current_page, limit, grafana_url, http_get_headers, verify_ssl,
                                                         client_cert, debug, session)
        print_horizontal_line()
        if len(dashboards) == 0:
            break
        else:
            current_page += 1
        await get_individual_dashboard_setting_and_save(dashboards, folder_path, log_file, grafana_url,
                                                        http_get_headers, verify_ssl, client_cert, debug, pretty_print,
                                                        uid_support, session)
        print_horizontal_line()


async def save_dashboards(folder_path, log_file, limit, grafana_url, http_get_headers, verify_ssl, client_cert, debug,
                          pretty_print, uid_support, session):
    current_page = 1
    dashboards = await get_all_dashboards_in_grafana(current_page, limit, grafana_url, http_get_headers, verify_ssl,
                                                     client_cert, debug, session)
    print_horizontal_line()
    await get_individual_dashboard_setting_and_save(dashboards, folder_path, log_file, grafana_url, http_get_headers,
                                                    verify_ssl, client_cert, debug, pretty_print, uid_support, session)
    print_horizontal_line()
