import os
from grafana_backup.dashboardApi import search_orgs, get_org
from grafana_backup.commons import to_python2_and_3_compatible_string, print_horizontal_line, save_json


async def main(args, settings):
    backup_dir = settings.get('BACKUP_DIR')
    timestamp = settings.get('TIMESTAMP')
    grafana_url = settings.get('GRAFANA_URL')
    http_get_headers_basic_auth = settings.get('HTTP_GET_HEADERS_BASIC_AUTH')
    verify_ssl = settings.get('VERIFY_SSL')
    client_cert = settings.get('CLIENT_CERT')
    debug = settings.get('DEBUG')
    pretty_print = settings.get('PRETTY_PRINT')
    session = settings.get('session')

    folder_path = '{0}/organizations/{1}'.format(backup_dir, timestamp)
    log_file = 'organizations_{0}.txt'.format(timestamp)

    if http_get_headers_basic_auth:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        await save_orgs(folder_path, log_file, grafana_url, http_get_headers_basic_auth, verify_ssl, client_cert, debug, pretty_print, session)
    else:
        print('[ERROR] Backing up organizations needs to set GRAFANA_ADMIN_ACCOUNT and GRAFANA_ADMIN_PASSWORD first.')
        print_horizontal_line()


async def get_all_orgs_in_grafana(grafana_url, http_get_headers, verify_ssl, client_cert, debug, session):
    (status, content) = await search_orgs(grafana_url,
                                    http_get_headers,
                                    verify_ssl,
                                    client_cert,
                                    debug, session)
    if status == 200:
        orgs = content
        print("There are {0} orgs:".format(len(orgs)))
        for org in orgs:
            print('name: {0}'.format(to_python2_and_3_compatible_string(org['name'])))
        return orgs
    else:
        print("get orgs failed, status: {0}, msg: {1}".format(status, content))
        return []


async def save_org_info(org_name, file_name, org_settings, folder_path, pretty_print):
    file_path = await save_json(file_name, org_settings, folder_path, 'organization', pretty_print)
    print("org: {0} -> saved to: {1}".format(org_name, file_path))


async def get_individual_org_info_and_save(orgs, folder_path, log_file, grafana_url, http_get_headers,
                                     verify_ssl, client_cert, debug, pretty_print, session):
    file_path = folder_path + '/' + log_file
    if orgs:
        with open(u"{0}".format(file_path), 'w') as log_file:
            for org in orgs:
                (status, content) = await get_org(org['id'], grafana_url, http_get_headers, session, verify_ssl, client_cert, debug)
                if status == 200:
                    await save_org_info(
                        to_python2_and_3_compatible_string(org['name']),
                        str(org['id']),
                        content,
                        folder_path,
                        pretty_print
                    )
                    log_file.write('{0}\t{1}\n'.format(org['id'], to_python2_and_3_compatible_string(org['name'])))


async def save_orgs(folder_path, log_file, grafana_url, http_get_headers, verify_ssl, client_cert, debug, pretty_print, session):
    orgs = await get_all_orgs_in_grafana(grafana_url, http_get_headers, verify_ssl,
                                   client_cert, debug, session)
    print_horizontal_line()
    await get_individual_org_info_and_save(orgs, folder_path, log_file, grafana_url, http_get_headers,
                                     verify_ssl, client_cert, debug, pretty_print, session)
    print_horizontal_line()
