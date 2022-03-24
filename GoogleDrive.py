import pickle
import os
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.auth.transport.requests import Request
import datetime
import json
from constants import google_oath, main_folder_key, ss_keys_file

def Create_Service(client_secret_file, api_name, api_version, *scopes):
    print(client_secret_file, api_name, api_version, scopes, sep='-')
    CLIENT_SECRET_FILE = client_secret_file
    API_SERVICE_NAME = api_name
    API_VERSION = api_version
    SCOPES = [scope for scope in scopes[0]]
    print(SCOPES)

    cred = None

    pickle_file = f'token_{API_SERVICE_NAME}_{API_VERSION}.pickle'
    # print(pickle_file)

    if os.path.exists(pickle_file):
        with open(pickle_file, 'rb') as token:
            cred = pickle.load(token)

    if not cred or not cred.valid:
        if cred and cred.expired and cred.refresh_token:
            cred.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            cred = flow.run_local_server(open_browser=False, access_type='online')

        with open(pickle_file, 'wb') as token:
            pickle.dump(cred, token)

    try:
        service = build(API_SERVICE_NAME, API_VERSION, credentials=cred)
        print(API_SERVICE_NAME, 'service created successfully')
        return service
    except Exception as e:
        print('Unable to connect.')
        print(e)
        return None

def convert_to_RFC_datetime(year=1900, month=1, day=1, hour=0, minute=0):
    dt = datetime.datetime(year, month, day, hour, minute, 0).isoformat() + 'Z'
    return dt

class googleDrive:
    """
    Hierarchy:
    - Year folder
        - Month folder
            - Month spreadsheet
                - General page
                - f"{FullName}_{uid}" page          # user 1 page
                - f"{FullName}_{uid}" page          # user 2 page
    """
    def __init__(self, oath):
        Gdrive_scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file",
                  "https://www.googleapis.com/auth/drive"]

        self.GDrive_service = Create_Service(oath, 'drive', 'v3', Gdrive_scope)

    def create_file_in_folder(self, parent_folder_key, file_name, file_type):
        """
        Creates file in folder
        :param parent_folder_key:
        :param file_name:
        :param file_type: 'folder' or 'spreadsheet'
        :return:
        """
        file_metadata = {
            'name': file_name,
            'mimeType': f'application/vnd.google-apps.{file_type}',
            'parents': [parent_folder_key]
        }
        sub_folder_key = self.GDrive_service.files().create(body =file_metadata).execute()['id']
        return sub_folder_key

    def create_drive_layout_for_date(self, main_folder_key, date):
        """
        Returns key of current month spreadsheet.
        If there is no current month spreadsheet - creates it.
        :param date: current date in string format dd/mm/yyyy
        :return:    f'{month}_{year}' - name of current spreadsheet
                    ss_key -  current month spreadsheet key.
        """
        day, month, year = date.split('/')

        years = self.get_folder_files(main_folder_key, file_type='folder')
        if (year in years.keys()):
            year_fold_key = years[year]
        else:
            year_fold_key = self.create_file_in_folder(main_folder_key, year, 'folder')
            print(f'{year} year folder created: {year_fold_key}')

        months = self.get_folder_files(year_fold_key, file_type='folder')
        if (f"{month}_{year}" in months.keys()):
            month_fold_key = months[f"{month}_{year}"]
        else:
            month_fold_key = self.create_file_in_folder(year_fold_key, f"{month}_{year}", 'folder')
            print(f'{month} month folder created: {month_fold_key}')

        spreadsheets = self.get_folder_files(month_fold_key, file_type='spreadsheet')
        if (f"{month}_{year}" in spreadsheets.keys()):
            ss_key = spreadsheets[f"{month}_{year}"]
        else:
            ss_key = self.create_file_in_folder(month_fold_key, f"{month}_{year}", 'spreadsheet')
            print(f'{month}_{year} spreadsheet created: {ss_key}')

        return f'{month}_{year}', ss_key

    def get_current_ss_key(self,main_folder_key, date):
        """
        Returns key of current month spreadsheet.
        If there is no current month spreadsheet - creates it.
        :param date: current date in string format dd/mm/yyyy
        :return: ss_key -  current month spreadsheet key.
        """
        ss_key = ''
        day, month, year = date.split('/')

        years = self.get_folder_files(main_folder_key, file_type='folder')
        if(year in years.keys()):
            year_fold_key = years[year]
        else:
            year_fold_key = self.create_file_in_folder(main_folder_key, year, 'folder')
            print(f'{year} year folder created: {year_fold_key}')

        months = self.get_folder_files(year_fold_key, file_type='folder')
        if(f"{month}_{year}" in months.keys()):
            month_fold_key = months[f"{month}_{year}"]
        else:
            month_fold_key = self.create_file_in_folder(year_fold_key, f"{month}_{year}", 'folder')
            print(f'{month} month folder created: {month_fold_key}')

        spreadsheets = self.get_folder_files(month_fold_key, file_type='spreadsheet')
        if(f"{month}_{year}" in spreadsheets.keys()):
            ss_key = spreadsheets[f"{month}_{year}"]
        else:
            ss_key = self.create_file_in_folder(month_fold_key, f"{month}_{year}", 'spreadsheet')
            print(f'{month}_{year} spreadsheet created: {ss_key}')
        return ss_key

    def get_folder_files(self, folder_key, file_type):
        """
        :param folder_key: key of current GDrive folder
        :param file_type: 'folder' or 'spreadsheet'
        :return:  dict[subfolder_name] = subfolder_key
        """
        response = self.GDrive_service.files().list(
            q=f"'{folder_key}' in parents and mimeType = 'application/vnd.google-apps.{file_type}'",
            spaces='drive',
            fields='nextPageToken, files(id, name)').execute()
        subfolders = {}
        for file in response.get('files', []):
            subfolders[file.get('name')] = file.get('id')
        return subfolders

def create_layout_for_years(years):
    layout_data = {}
    months = ['01','02','03','04','05','06','07','08','09','10','11','12']
    day = '01'
    gd = googleDrive(google_oath)
    for year in years:
        layout_data[year] = {}
        for month in months:
            # layout_data[year][month] = {}
            date = day + '/' + month + '/' + year
            ss_name, ss_key = gd.create_drive_layout_for_date(main_folder_key, date)
            layout_data[year][month] = ss_key
    return layout_data

def create_ss_keys_for_i_years(i = 4):
    """

    :param i: number of years from 2021 to 2021 + i - 1
    :return:
    """
    years = [str(2021 + i) for i in range(i)]
    layout_data = create_layout_for_years(years)

    # december 2020:
    gd = googleDrive(google_oath)
    ss_name, ss_key = gd.create_drive_layout_for_date(main_folder_key, '01/12/2020')
    layout_data['2020'] = {'12':ss_key}

    print(layout_data)

    with open(ss_keys_file, 'w') as fp:
        json.dump(layout_data, fp)

    return layout_data


if __name__ == '__main__':
    create_ss_keys_for_i_years(1)