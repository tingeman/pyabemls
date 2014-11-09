from tables import *
import numpy as np
import re
import os.path
import datetime as dt
from matplotlib.dates import num2date, drange
import sqlite3
from pandas import DataFrame
import pdb
from lxml import etree

def remove_comments(line, sep):
    for s in sep:
        line = line.split(s)[0]
    return line.strip()


class ABEMLS_project():
    """Class to handle getting data from an ABEM Terrameter LS project file

    """

    GETDATA_SQL = """
        SELECT
            DPV.TaskID,
            DPV.MeasureID,
            DPV.Channel,
            DPV.DatatypeID,
            DP_ABMN.APosX,DP_ABMN.APosY,DP_ABMN.APosZ,
            DP_ABMN.BPosX,DP_ABMN.BPosY,DP_ABMN.BPosZ,
            DP_ABMN.MPosX,DP_ABMN.MPosY,DP_ABMN.MPosZ,
            DP_ABMN.NPosX,DP_ABMN.NPosY,DP_ABMN.NPosZ,
            DPV.DataValue,
            DPV.DataSDev,
            DPV.MCycles,
            Measures.Time,
            Measures.PosLatitude,
            Measures.PosLongitude,
            Measures.PosQuality,
            Measures.IntPowerVolt,
            Measures.ExtPowerVolt,
            Measures.Temp
        FROM DPV, DP_ABMN, DP_MEASURE, Measures
        WHERE DPV.MeasureID=DP_MEASURE.MeasureID AND DP_ABMN.ID=DP_MEASURE.DPID AND Measures.ID=DP_MEASURE.MeasureID
            AND DPV.DatatypeID=5
            AND DPV.Channel=1
    """

    GET_TASK_SQL = """
        SELECT
            Measures.Time,
            DPV.TaskID,
            DPV.MeasureID,
            DPV.Channel,
            DPV.DatatypeID,
            DP_ABMN.APosX,DP_ABMN.APosY,DP_ABMN.APosZ,
            DP_ABMN.BPosX,DP_ABMN.BPosY,DP_ABMN.BPosZ,
            DP_ABMN.MPosX,DP_ABMN.MPosY,DP_ABMN.MPosZ,
            DP_ABMN.NPosX,DP_ABMN.NPosY,DP_ABMN.NPosZ,
            DPV.DataValue,
            DPV.DataSDev,
            DPV.MCycles,
            DPV.SeqNum
        FROM DPV, DP_ABMN, DP_MEASURE, Measures
        WHERE
            DPV.TaskID=? AND
            DPV.MeasureID=DP_MEASURE.MeasureID AND
            DP_ABMN.ID=DP_MEASURE.DPID AND
            DP_ABMN.ID=DPV.DPID AND
            Measures.ID=DP_MEASURE.MeasureID
    """

    GET_ELECTRODETESTS = """
        SELECT ID
             , TaskID
             , StationID
             , SwitchNumber
             , SwitchAddress
             , PosX
             , PosY
             , PosZ
             , ResistanceValue
             , CurrentValue
             , TestStatus
             , UserSetting
             , TxStatus
             , Time
        FROM ElectrodeTestData
    """

    GET_TASK_ELECTRODETEST = """
        SELECT ID
             , TaskID
             , StationID
             , SwitchNumber
             , SwitchAddress
             , PosX
             , PosY
             , PosZ
             , ResistanceValue
             , CurrentValue
             , TestStatus
             , UserSetting
             , TxStatus
             , Time
        FROM ElectrodeTestData
        WHERE TaskID=?
    """


    # GET_TASKS_INFO_SQL = """
    #     SELECT
    #         Tasks.ID,
    #         Tasks.Name,
    #         Tasks.PosX, Tasks.PosY, Tasks.PosZ,
    #         Tasks.SpacingX, Tasks.SpacingY, Tasks.SpacingZ,
    #         Tasks.ArrayCode,Tasks.Time,
    #         COUNT(*) AS ndat
    #     FROM (
    #         SELECT *
    #         FROM DPV
    #         WHERE
    #             DPV.Channel>0 AND DPV.Channel<13
    #         GROUP BY
    #             DPV.TaskID, DPV.MeasureID, DPV.Channel
    #     ) AS NdatTable
    #     LEFT JOIN Tasks ON Tasks.ID=NdatTable.TaskID
    # """

    GET_TASK_INFO_SQL_BACKUP = """
        SELECT
            Tasks.ID,
            Tasks.Name,
            Tasks.PosX, Tasks.PosY, Tasks.PosZ,
            Tasks.SpacingX, Tasks.SpacingY, Tasks.SpacingZ,
            Tasks.ArrayCode,Tasks.Time,
            COUNT(*) AS ndat
        FROM (
            SELECT TaskID, MeasureID, Channel
            FROM DPV
            WHERE
                Channel>0 AND Channel<13 AND TaskID=?
            GROUP BY
                TaskID, MeasureID, Channel
        ) AS NdatTable, Tasks
        WHERE Tasks.ID=NdatTable.TaskID
    """


    GET_TASK_INFO_SQL_BACKUP2 = """
        SELECT
            Tasks.ID,
            Tasks.Name,
            Tasks.PosX, Tasks.PosY, Tasks.PosZ,
            Tasks.SpacingX, Tasks.SpacingY, Tasks.SpacingZ,
            Tasks.ArrayCode,Tasks.Time,
            COUNT(DISTINCT ndt.ID) as nData,
            COUNT(DISTINCT ndt.DPID) as nDipoles,
            COUNT(DISTINCT e.ID) as nECRdata
        FROM Tasks
        LEFT JOIN ElectrodeTestData as e ON Tasks.ID=e.TaskID
        LEFT JOIN (SELECT * FROM DPV WHERE Channel>0 AND Channel<13) as ndt ON ndt.TaskID=Tasks.ID
        GROUP BY Tasks.ID
    """

    GET_TASK_INFO_SQL = """
        SELECT
            Tasks.ID,
            Tasks.Name,
            Tasks.PosX, Tasks.PosY, Tasks.PosZ,
            Tasks.SpacingX, Tasks.SpacingY, Tasks.SpacingZ,
            Tasks.ArrayCode,Tasks.Time,
            ts1.Value as ProtocolFile,
            ts2.Value as SpreadFile,
            ts4.Value as BaseReference,
            COUNT(DISTINCT ndt.ID) as nData,
            COUNT(DISTINCT ndt.DPID) as nDipoles,
            COUNT(DISTINCT e.ID) as nECRdata
        FROM Tasks
        LEFT JOIN ElectrodeTestData as e ON Tasks.ID=e.TaskID
        LEFT JOIN (SELECT * FROM DPV WHERE Channel>0 AND Channel<13)            as ndt ON ndt.TaskID=Tasks.ID
        LEFT JOIN (SELECT * FROM TaskSettings WHERE Setting="ProtocolFile")     as ts1 ON ts1.key1=Tasks.ID
        LEFT JOIN (SELECT * FROM TaskSettings WHERE Setting="SpreadFile")       as ts2 ON ts2.key1=Tasks.ID
        LEFT JOIN (SELECT * FROM TaskSettings WHERE Setting="BaseReference")    as ts4 ON ts4.key1=Tasks.ID
        GROUP BY Tasks.ID
    """

    # GET_TASKS_INFO_SQL = """
    #     SELECT DPV.TaskID, COUNT(*)
    #     FROM DPV
    #     WHERE
    #         DPV.Channel>0 AND DPV.Channel<13
    #     GROUP BY
    #         DPV.TaskID, DPV.MeasureID, DPV.Channel
    # """


    def __init__(self, filename, ):
        # Define instance variables
        self.filename = None
        self.tasks = None
        self.task_cols = None
        self.spread_files = dict()
        self.datatypes = dict()

        conn = sqlite3.connect(filename)
        cur = conn.cursor()
        self.get_tasklist(cur=cur)
        self.get_datatypes_from_db(cur=cur)
        cur.close()
        conn.close()
        self.filename = filename

    def execute_sql(self, sql, cur=None, args=None):
        temp_cur = False
        if cur is None:
            temp_cur = True
            conn = sqlite3.connect(self.filename)
            cur = conn.cursor()

        if not args:
            cur.execute(sql)
        else:
            cur.execute(sql, args)

        rows = cur.fetchall()
        cols = [c[0] for c in cur.description]

        if temp_cur:
            cur.close()
            conn.close()

        return rows, cols

    def get_datatypes_from_db(self, cur=None):
        """Get datatypes table from the db file

        """
        temp_cur = False
        if cur is None:
            temp_cur = True
            conn = sqlite3.connect(self.filename)
            cur = conn.cursor()

        cur.execute("SELECT * FROM Datatype")

        rows = cur.fetchall()
        column_titles = cur.description

        if temp_cur:
            cur.close()
            conn.close()

        self.datatypes = dict()

        for row in rows:
            self.datatypes[row[0]] = {
                    column_titles[1][0]: row[1],
                    column_titles[2][0]: row[2],
                    column_titles[3][0]: row[3]
            }

    def get_data(self):
        """Get data from SQLITE file, return rows and column titles.
        """

        conn = sqlite3.connect(self.filename)
        cur = conn.cursor()

        cur.execute(self.GETDATA_SQL)

        rows = cur.fetchall()
        column_titles = cur.description
        cur.close()
        conn.close()

        return rows, column_titles

    def get_tasklist(self, cur=None):
        """Read tasks table from db file

        """
        temp_cur = False
        if cur is None:
            temp_cur = True
            conn = sqlite3.connect(self.filename)
            cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM Tasks")

        try:
            ntasks = cur.fetchall()[0][0]
        except:
            ntasks = 0

        cur.execute(self.GET_TASK_INFO_SQL)
        tasks = cur.fetchall()
        #tasks = []
        #for n in xrange(1,ntasks+1):
        #    cur.execute(self.GET_TASK_INFO_SQL_2, (n,))
        #    tasks.append(cur.fetchall()[0])

        task_cols = [c[0] for c in cur.description]

        result = DataFrame(tasks, columns=task_cols)

        self.tasks=result

        if temp_cur:
            cur.close()
            conn.close()

        return result


    def list_tasks(self):
        """Print a nice list of the tasks

        """
        if self.tasks is None:
            self.get_tasklist()

        print "Tasks in project:"
        for id, t in self.tasks.iterrows():
            # print ("Task ID: {0}   "
            #        "Name: {1:8}  "
            #        "Edist: {2}   "
            #        "Array: {3}   "
            #        "Datapts: {4}   "
            #        "Time: {5}".format(t[0],t[1],t[5],t[8],t[10],t[9]))
            print "-"*40
            print t

    def get_task(self, task_id=1, condensed=False, cur=None):
        """Read task data from db file

        If condensed=True, all parameters for one channel will be collected
        in one row of the resulting array.
        """

        temp_cur = False
        if cur is None:
            temp_cur = True
            conn = sqlite3.connect(self.filename)
            cur = conn.cursor()

        #pdb.set_trace()
        cur.execute(self.GET_TASK_SQL, (task_id,))
        task = cur.fetchall()
        task_cols = [c[0] for c in cur.description]

        if task:
            result = DataFrame(task, columns=task_cols)
        else:
            result = DataFrame()

        if self.tasks.nECRdata[self.tasks.ID == task_id].values[0] > 0:
            etest = self.get_electrodetest(task_id=task_id, cur=cur)
        else:
            etest = DataFrame()

        if temp_cur:
            cur.close()
            conn.close()

        if condensed:
            result = condense_measurements(result, self.datatypes)

        return result, etest

    def get_electrodetest(self, task_id=None, cur=None):
        """Read electrode test data from db file. Test data will be read for
        the task given in task_id. If task_id is None, all test data will be
        read.
        """

        temp_cur = False
        if cur is None:
            temp_cur = True
            conn = sqlite3.connect(self.filename)
            cur = conn.cursor()

        #pdb.set_trace()
        if task_id is not None:
            cur.execute(self.GET_TASK_ELECTRODETEST, ('{0}'.format(task_id),))
        else:
            cur.execute(self.GET_ELECTRODETESTS)

        etest = cur.fetchall()
        etest_cols = [c[0] for c in cur.description]

        result = DataFrame(etest, columns=etest_cols)

        if temp_cur:
            cur.close()
            conn.close()

        return result


    def get_spreadfile(self, fname, path=""):
        if not fname:
            raise ValueError('No valid filename passed to get_spreadfile.')
        basename = os.path.basename(fname)
        if basename in self.spread_files.keys():
            tree = self.spread_files[basename]
        else:
            filename = os.path.join(path,basename)
            tree = etree.parse(filename)
            self.spread_files[basename] = tree
        return tree


    def get_electrode_id(self, posx, posy=None, posz=None, path="",
                         spreadfile="", task_id=None):
        #pdb.set_trace()
        if not spreadfile and task_id is not None:
            spreadfile = self.tasks.SpreadFile[self.tasks.ID==task_id][0]

        tree = self.get_spreadfile(spreadfile, path)
        xpstring = ".//Electrode[X//text()=' {0} '".format(posx)
        if posy is not None:
            xpstring += " and Y//text()=' {0} '".format(posy)
        if posz is not None:
            xpstring += " and Z//text()=' {0} '".format(posz)
        xpstring += "]//Id//text()"

        try:
            return int(tree.xpath(xpstring)[0])
        except:
            print "Could not find electrode: " + xpstring
            return None




def condense_measurements(data, datatype_dict):
    """Condense measurements such that all measurement values for a specific
    channel and MeasureID is in the same row

    data:           a DataFrame as returned by ABEMLS_project.get_task()
    datatype_dict:  a dictionary of datatypes as stored in ABEMLS_project.datatypes
    """

    # raise NotImplementedError('condense_measurements method not yet finished!')

    rep_dict = {u'\u03c1': r'rho_',
                u'\u0394': r'd',
                u'\u03a9': r'Ohm'}


    MeasureIDs = data.MeasureID.unique()
    channels = data.Channel.unique()

    result = None

    for mid in MeasureIDs:

        # Here we should get out the Current:

        # Ivalue = ....
        # Isdev = ....

        # So that we can add it below...

        for c in channels:
            if (c<1) or (c>12):
                # only handle data channels
                continue

            dat = data[(data.MeasureID==mid) & (data.Channel==c)]

            if len(dat) == 0:
                continue

            # Prepare new DataFrame
            tmp = dat.ix[dat.index[0]].copy()
            tmp = tmp.drop(['DataValue', 'DataSDev', 'SeqNum',
                            'DatatypeID'])
            df = DataFrame(data=np.atleast_2d(tmp.values),
                           columns=tmp.index)

            for dtid in sorted(dat.DatatypeID.unique()):
                d = dat[dat.DatatypeID==dtid]
                if len(d.SeqNum)==0:
                    # No data with this datatype
                    continue
                elif len(d.SeqNum)>1:
                    # Loop over all sequence numbers and add a subscript when
                    # adding the name
                    for sn in d.SeqNum.unique():
                        pass
                else:
                    # We have only one item with this datatype, add it...
                    n = datatype_dict[dtid]['Name']

                    # Replace known non-ascii unicode chars from names
                    for k,v in rep_dict.items():
                        n = n.replace(k,v)

                    df[n] = np.array(d.DataValue, dtype=float)[0]
                    df[n+'_SDev'] = np.array(d.DataSDev, dtype=float)[0]

            if result is None:
                result = df.copy()
            else:
                result = result.append(df, ignore_index=True)


    return result



