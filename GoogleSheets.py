import gspread as gsp
from oauth2client.service_account import ServiceAccountCredentials

#from GoogleDrive import Create_Service

import calendar
import datetime
import json

from constants import ss_keys_file

class googleSheets:
    """
    Hierarchy:
    - Year folder
        - Month folder
            - Month spreadsheet
                - General page
                - f"{FullName}_{uid}" page          # user 1 page
                - f"{FullName}_{uid}" page          # user 2 page
    """
    def __init__(self, credentials):
        """
        :param credentials: Google service account credentials
        """
        GSheets_scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']

        self.creds = ServiceAccountCredentials.from_json_keyfile_name(credentials, GSheets_scope)
        self.GSheets_client = gsp.authorize(self.creds)

    def get_current_ss_key(self, date=None):
        """
        Returns key of current month spreadsheet.
        :param date: current date in string format dd/mm/yyyy
        :return: ss_key -  current month spreadsheet key.
        """
        if(date == None):
            date = datetime.datetime.now().date()                          # current datetime
            date = '/'.join(str(date).split('-'))
            year, month, day = date.split('/')
        else:
            day, month, year = date.split('/')

        # Opens json file with spreadsheet keys and takes it from there by date
        with open(ss_keys_file, 'r') as fp:
            ss_keys_dict = json.load(fp)
        ss_key = ss_keys_dict[year][month]
        return ss_key

    def add_data_to_cells(self, user_ws, checkInOut):
        """

        :param user_ws:
        :param checkInOut:

        :return: json result of data incertion
        """
        # todo: delete later
        # res = user_ws.append_row(checkInOut, value_input_option="USER_ENTERED")


        ff_row = len(user_ws.col_values(13)) + 1 # first free row in "M" column
        cell_list = user_ws.range(f'M{ff_row}:U{ff_row}')

        checkInOut.append(f'=IF($R{ff_row}="OUT",$N{ff_row}-$N{ff_row-1},"")')
        for i, val in enumerate(checkInOut):  # gives us a tuple of an index and value
            cell_list[i].value = val  # use the index on cell_list and the val from cell_values

        res = user_ws.update_cells(cell_list, value_input_option="USER_ENTERED")
        return res

    def add_checkInOut(self, ws_name, checkInOut):
        """
        Adds checkIn or checkOut to correct spreadsheet and worksheet
        :param ws_name:         worksheet name : f"{FullName}_{uid}" (to make unique keys)
        :param checkInOut:      checkInOut data in list format

        :return: json result of data incertion
        """
        msg_date = checkInOut[0] # first el of checkInOut is the date of the message
        self.ss_key = self.get_current_ss_key(msg_date)
        self.ss = self.GSheets_client.open_by_key(self.ss_key)  # current spreadsheet


        if(self.check_WS_existance(ws_name)==False):
            if(self.check_WS_existance("General Page") == False):
                general_ws = self.create_GeneralPage()
                if (self.check_WS_existance("Sheet1")):
                    self.ss.del_worksheet(self.ss.worksheet('Sheet1'))
            else:
                general_ws = self.ss.worksheet("General Page")
            user_ws = self.ss.add_worksheet(ws_name,0,0)
            self.userDefLayout(user_ws, general_ws)
        else:
            user_ws = self.ss.worksheet(ws_name)      # current worksheet

        res = self.add_data_to_cells(user_ws, checkInOut)
        print(f'SS {self.ss.title} updated WS {ws_name} for {checkInOut[0:2]}')
        return res

    def userDefLayout(self, user_ws, general_ws):
        """
        Adds user default layout
        :param user_ws:       user worksheet
        :param user_ws:       general worksheet
        :return:
        """
        ll = user_ws.title.split("_")
        ll = ll[:-1]
        username = ""
        for l in ll:
            username += l + "_"
        username = username[:-1]


        ### MONTH TABLE  CREATION : ####

        user_ws.append_row(["Date", "Place", "Beggining", "Ending", "BrakeTime", "Total Work", "Clean Work Hours"])    # 2
        user_ws.insert_row(["", "", username])                                             # 1

        ss_month, ss_year = self.ss.title.split('_')
        ss_month, ss_year = int(ss_month), int(ss_year)
        days_num=calendar.monthrange(ss_year, ss_month)[1]    # days num in current mount

        cell_list = user_ws.range(f'A3:G{3 + days_num}')

        for i in range(days_num):  # gives us a tuple of an index and value
            day = f"{i + 1}"
            if(len(str(i + 1)) < 2):
                day = f"0{i+1}"
            month = f"{ss_month}"
            if(len(str(ss_month)) < 2):
                month = f"0{ss_month}"
            # date
            cell_list[7 * i].value = \
                f"{day}/{ss_month}/{ss_year}"
            # Place
            cell_list[7 * i+1].value = \
                ''
            # First work of the day IN time
            cell_list[7 * i+2].value = \
                f'=if(countif($M$3:$M,$A{i+3})>0,ArrayFormula(MIN(FILTER($N$3:N,$M$3:M=$A{i+3},$R$3:R="IN"))),"")'
            # Last work of the day OUT time
            cell_list[7 * i+3].value = \
                f'=if(countif($M$3:$M,$A{i+3})>0,ArrayFormula(MAX(FILTER($N$3:N,$M$3:M=$A{i+3},$R$3:R="OUT"))),"")'
            # Brake Time
            cell_list[7 * i+4].value = \
                f'=if(countif($M$3:$M,$A{i+3})>0,ROUNDDOWN($F{i+3}/time(4,0,0))*time(0,15,0),"")'
            # Total daywork time
            cell_list[7 * i+5].value = \
                f'=if(countif($M$3:$M,$A{i+3})>0,ArrayFormula(SUM(FILTER($U$3:U,$M$3:M=$A{i+3},$R$3:R="OUT"))),"")'
            # Difference between woking hours and breaking time
            cell_list[7 * i + 6].value = \
                f'=if($F{i+3}<>"",$F{i+3}-$E{i+3},"")'

        total_row = [  "Total:", "","", "",
                       f"=ROUND(SUM(0,$E3:$E${2+days_num})*24,2)",
                       f"=ROUND(SUM(0,$F$3:$F${2+days_num})*24,2)",
                       f"=$F${2+days_num+1}-$E${2+days_num+1}"]

        for j in range(7):
            cell_list[7*days_num+j].value = total_row[j]

        res = user_ws.update_cells(cell_list, value_input_option="USER_ENTERED")

        cell_list = user_ws.range(f'A{5 + days_num}:L{6 + days_num}')

        title_row = [   "User", "Work days", "Trips", "Hour income",
                        "100%", "125%", "150%", "200%",
                        "Total hours", "Total payment",
                        "Health addition", "Total + HA"]

        for j in range(12):
            cell_list[j].value = title_row[j]

        user_row = [    username,
                        f'=COUNTIF($C$3:$C${2+days_num},">0")',
                        f'=IF(5.9*2*$B${2 + days_num + 4}<=200,5.9*2*$B${2 + days_num + 4},213)',
                        "",
                        f'=$I${2 + days_num + 4}',
                        "",
                        "",
                        "",
                        f'=$G${2 + days_num + 1}',
                        f'=$C${2 + days_num + 4}+ROUND((1*E{2 + days_num + 4}+1.25*F{2 + days_num + 4}+1.5*G{2 + days_num + 4}+2*H{2 + days_num + 4})*D{2 + days_num + 4},2)',
                        f'=ROUND(IF(I{2 + days_num + 4}<=182,SUM(432/182*I{2 + days_num + 4})*0.58,SUM(432*0.58)),2)',
                        f'=$J${2 + days_num + 4}+$K${2 + days_num + 4}']
        for j in range(12):
            cell_list[12 + j].value = user_row[j]

        res = user_ws.update_cells(cell_list, value_input_option="USER_ENTERED")

        ### GENERAL PAGE UPDATE : #######

        ff_row = len(general_ws.col_values(1)) + 1  # first free row in "A" column
        cell_list = general_ws.range(f'A{ff_row}:L{ff_row}')

        for k in range(12):  # gives us a tuple of an index and value
            cell_list[k].value = f"='{user_ws.title}'!${chr(ord('A')+k)}${2 + days_num + 4}"  # use the index on cell_list and the val from cell_values

        res = general_ws.update_cells(cell_list, value_input_option="USER_ENTERED")

        ### IN/OUT TABLE  CREATION : ####

        MD_cell = user_ws.range(f'P1:P1')   # Month data cell
        MD_cell[0].value = "Month data"
        user_ws.update_cells(MD_cell)

        cols = ["","","","","Month data","","","","",
            "DATE","TIME","uID","USERNAME",
                       "FULL NAME","IN / OUT","Latitude","Longtitude", "Work time"]

        cell_list = user_ws.range(f'M1:U2')
        for i, col_name in enumerate(cols):  # gives us a tuple of an index and value
            cell_list[i].value = col_name  # use the index on cell_list and the val from cell_values

        res = user_ws.update_cells(cell_list)

        return res

    def create_GeneralPage(self, page_exist = False):
        """
        Creates General page for spreadsheet
        :return: general_ws     - general worksheet object
        """
        if(page_exist):
            general_ws = self.ss.worksheet("General Page")
        else:
            general_ws = self.ss.add_worksheet("General Page",0,0)
        general_ws.append_row(["User",
                               "Work days",
                               "Trips",
                               "Hour income",
                               "100%",
                               "125%",
                               "150%",
                               "200%",
                               "Total hours",
                               "Total payment",
                               "Health addition",
                               "Total + HA"])
        return general_ws

    def check_WS_existance(self, ws_name):
        """
        Checks if user worksheets exist, o.w. creates it
        :param ws_name:      worksheet_name : f"{FullName}_{uid}" (to make unique keys)
        :return: True if worksheet exists
        """
        worksheets = self.ss.worksheets()
        worksheets = [sheet.title for sheet in worksheets]
        return ws_name in worksheets

    def update_GeneralPage(self, date = None):
        """
        Recalculates user data on general page
        :return:
        """
        # todo: maybe incorrect
        self.ss_key = self.get_current_ss_key(date)
        self.ss = self.GSheets_client.open_by_key(self.ss_key)  # current spreadsheet
        self.ss.values_clear("General Page!A1:Z1000")
        general_ws = self.create_GeneralPage(page_exist=True)

        ss_month, ss_year = self.ss.title.split('_')
        ss_month, ss_year = int(ss_month), int(ss_year)
        days_num = calendar.monthrange(ss_year, ss_month)[1]    # days num in current mount

        ws_number = len(self.ss.worksheets())
        i = 0
        cell_list = general_ws.range(f'A2:L{ws_number}')
        for ws in self.ss.worksheets():
            if(ws.title != 'General Page'):
                for k in range(12):  # gives us a tuple of an index and value
                    cell_list[12*i+k].value = f"='{ws.title}'!${chr(ord('A') + k)}${2 + days_num + 4}"  # use the index on cell_list and the val from cell_values
                i += 1
        res = general_ws.update_cells(cell_list, value_input_option="USER_ENTERED")

        return cell_list





if __name__ == '__main__':
    from constants import google_credentials
    gs = googleSheets(google_credentials)
    gs.update_GeneralPage()
    # ws_name = 'Vitaly Pankratov_88005553535'
    # #
    # res = gs.add_checkInOut(ws_name=ws_name,
    #                         checkInOut=["01/01/2021", "13:01:44", 88005553535, 'Stayermax', "Vitaly Pankratov", 'IN',32.819453, 34.999706])
    # res = gs.add_checkInOut(ws_name=ws_name,
    #                         checkInOut=["01/01/2021", "23:25:44", 88005553535, 'Stayermax', "Vitaly Pankratov", 'OUT',32.819453, 34.999706])
    # #
    # ws_name = "Vitaly Pankratov_2128506"
    # res = gs.add_checkInOut(ws_name=ws_name,
    #                         checkInOut=["03/01/2021", "21:01:44", 2128506, 'Stayermax', "Vitaly Pankratov", 'IN',32.819453, 34.999706])
    # res = gs.add_checkInOut(ws_name=ws_name,
    #                         checkInOut=["03/01/2021", "22:01:44", 2128506, 'Stayermax', "Vitaly Pankratov", 'OUT',32.819453, 34.999706])
