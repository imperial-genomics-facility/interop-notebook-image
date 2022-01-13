import json
from shutil import copy2
import pandas as pd
import numpy as np
import os, tempfile, subprocess, json, logging
from interop_data_plot import read_interop_data
from interop_data_plot import read_runinfo_xml
from interop_data_plot import get_summary_stats

def get_intensity_data(extractionDf, colors):
    try:
        intensity_columns = [
            c for c in extractionDf.columns
                if c.startswith('MaxIntensity_')]
        if len(intensity_columns) == 0:
            raise ValueError('No intensity columns found')
        extractionDf['Lane'] = extractionDf['Lane'].astype(int)
        extractionDf['Cycle'] = extractionDf['Cycle'].astype(int)
        for c in intensity_columns:
            extractionDf[c] = extractionDf[c].astype(float)
        formatted_data = list()
        for lane_id, l_data in extractionDf.groupby('Lane'):
            for cycle, c_data in l_data.groupby('Cycle'):
                row = {'Lane':lane_id, 'Cycle':cycle}
                for c in intensity_columns:
                    row.update({c: c_data[c].median()})
                formatted_data.append(row)
        formatted_data = pd.DataFrame(formatted_data)
        chart_data = dict()
        labels = []
        for lane_id, l_data in formatted_data.groupby('Lane'):
            labels = l_data.sort_values('Cycle').set_index('Cycle').index.tolist()
            lane_data = list()
            for c, color in zip(intensity_columns, colors):
                intensity_data = l_data.sort_values('Cycle').set_index('Cycle')[c].astype(int).values.tolist()
                lane_data.append({
                    "label": c,
                    "data": intensity_data,
                    "color": color })
            chart_data.update({lane_id: lane_data})
        return {"chart_data":chart_data, "labels":labels}
    except Exception as e:
        raise ValueError(e)


def get_table_data(tile, q2030, extraction, empiricalphasing, error, runinfo):
    merged_data = \
      get_summary_stats(
        tileDf=tile,
        q2030Df=q2030,
        extractionDf=extraction,
        empiricalPhasingDf=empiricalphasing,
        errorDf=error,
        runinfoDf=runinfo)
    merged_data.columns = \
        [c.capitalize().replace("_"," ") \
             for c in merged_data.columns]
    table_data = \
        merged_data.\
            to_html(
                index=False,
                justify="center",
                border=0,
                classes="table table-sm table-striped").\
            replace('\n','')
    return table_data


def get_surface_data(tilesDf):
    surface1_data = dict()
    surface2_data = dict()
    tileDf_filt = tilesDf[tilesDf['Lane']!=''].copy()
    tileDf_filt['Lane'] = tileDf_filt['Lane'].astype(int)
    tileDf_filt['Tile'] = tileDf_filt['Tile'].astype(int)
    tileDf_filt['ClusterCountPF'] = tileDf_filt['ClusterCountPF'].astype(float)
    surface1_zdata = list()
    surface2_zdata = list()
    lanes = list()
    for lane_id,l_data in tileDf_filt.groupby('Lane'):
        lanes.append('Lane {0}'.format(lane_id))
        surface1_zdata.append(
            list(l_data[l_data['Tile'] < 2200].\
                groupby('Tile')['ClusterCountPF'].agg('median').values))
        surface2_zdata.append(
            list(l_data[l_data['Tile'] >= 2200].\
                groupby('Tile')['ClusterCountPF'].agg('median').values))
    surface1_tiles = \
        list(tileDf_filt[(tileDf_filt['Lane']==lane_id) & (tileDf_filt['Tile'] < 2200)].\
             groupby('Tile').groups.keys())
    surface2_tiles = \
        list(tileDf_filt[(tileDf_filt['Lane']==lane_id) & (tileDf_filt['Tile'] >= 2200)].\
             groupby('Tile').groups.keys())
    surface1_tiles = [
        'Tile {0}'.format(t)
            for t in surface1_tiles
                if int(t) < 2200]
    surface2_tiles = [
        'Tile {0}'.format(t)
            for t in surface2_tiles
                if int(t) >= 2200]
    surface1_data = {
        "z":surface1_zdata,
        "x":surface1_tiles,
        "y":lanes}
    surface2_data = {
        "z":surface2_zdata,
        "x":surface2_tiles,
        "y":lanes}
    return {"surface1":surface1_data, "surface2":surface2_data}


def get_cluster_and_density_counts(tilesDf, colors):
    tilesDf.dropna(inplace=True)
    tilesDf['ClusterCountPF'] = tilesDf['ClusterCountPF'].astype(float)
    tilesDf['ClusterCount'] = tilesDf['ClusterCount'].astype(float)
    tilesDf['Density'] = tilesDf['Density'].astype(float)
    tilesDf['DensityPF'] = tilesDf['DensityPF'].astype(float)
    tilesDf['Lane'] = tilesDf['Lane'].astype(int)
    density_box_data = list()
    lane_data = list()
    clusterCount_box_data = list()
    for lane_id,l_data in tilesDf.groupby('Lane'):
        clusterCount_box_data.append({
            'ClusterCount': l_data['ClusterCount'].values.tolist(),
            'ClusterCountPF': l_data['ClusterCountPF'].values.tolist(),
            'lane_id': lane_id,
            'color': colors[lane_id - 1]})
        density_box_data.append({
            'Density': l_data['Density'].values.tolist(),
            'DensityPF': l_data['DensityPF'].values.tolist(),
            'lane_id': lane_id,
            'color': colors[lane_id - 1]})
    return clusterCount_box_data, density_box_data


def get_qscore_bin_data(qByLane, colors):
    key_cols = ['Lane']
    for i in qByLane.columns.tolist():
        if i.startswith("Bin_"):
            key_cols.append(i)
    qByLane.fillna(0,inplace=True)
    qByLane_filt = qByLane[qByLane['Lane'].isin(['0','1','2','3','4','5','6','7','8'])].copy()
    qByLane_filt = qByLane_filt.applymap(lambda x: int(x))
    max_q30_line = \
        int(qByLane_filt.groupby('Lane').agg('mean')[key_cols[-1]].max()) + 10000
    key_cols.pop(0)
    qscore_dist_data = list()
    for lane_id,l_data in qByLane_filt.groupby('Lane'):
        lane_id = int(lane_id)
        qscore_dist_data.append({
            "label": 'Lane {0}'.format(lane_id),
            "data": list(l_data[key_cols].mean().astype(int).values.tolist()),
            "backgroundColor":colors[lane_id - 1]})
    return {'data': qscore_dist_data, 'labels': key_cols}


def get_QScore_by_cycle_data(q2030Df, colors):
    q2030Df['Lane'] = q2030Df['Lane'].astype(int)
    q2030Df['Cycle'] = q2030Df['Cycle'].astype(int)
    q2030Df['MedianQScore'] = q2030Df['MedianQScore'].astype(int)
    q2030Df['MedianQScore'] = \
        np.where(q2030Df['MedianQScore'] > 50,0,q2030Df['MedianQScore'])
    q2030Df['Tile'] = q2030Df['Tile'].astype(int)
    qscore_bar_plots = list()
    for lane_id,l_data in q2030Df.groupby('Lane'):
        lane_id = int(lane_id)
        dataset = list(l_data.groupby('Cycle')['MedianQScore'].mean().values.tolist())
        dataset = [int(i) for i in dataset]
        labels = list(l_data.groupby('Cycle')['MedianQScore'].mean().index.tolist())
        qscore_bar_plots.append({
            'lane_id': lane_id,
            'labels': labels,
            'data': dataset,
            'backgroundColor': colors[lane_id-1],
        })
    return qscore_bar_plots

def get_occupied_pass_filter(imaging_table_data):
    mod_headers = [
        'Lane', 'Tile', 'Cycle', 'Read', 'Cycle Within Read', 'Density(k/mm2)',
        'Density Pf(k/mm2)', 'Cluster Count (k)', 'Cluster Count Pf (k)', '% Pass Filter',
        '% Aligned', 'Legacy Phasing Rate', 'Legacy Prephasing Rate', 'Error Rate',
        '%>= Q20', '%>= Q30', 'P90_RED', 'P90_GREEN', '% No Calls', '% Base_A',
        '% Base_C', '% Base_G', '% Base_T', 'Fwhm_RED', 'Fwhm_GREEN', 'Corrected_A',
        'Corrected_C', 'Corrected_G', 'Corrected_T', 'Called_A', 'Called_C',
        'Called_G', 'Called_T', 'Signal To Noise', 'Phasing Weight', 'Prephasing Weight',
        'Phasing Slope', 'Phasing Offset', 'Prephasing Slope', 'Prephasing Offset',
        'Minimum Contrast_RED', 'Minimum Contrast_GREEN', 'Maximum Contrast_RED',
        'Maximum Contrast_GREEN', 'Surface', 'Swath', 'Tile Number',
        'Cluster Count Occupied (k)', '% Occupied']
    colors = [
        'rgb(255, 99, 132)',
        'rgb(255, 159, 64)',
        'rgb(255, 205, 86)',
        'rgb(75, 192, 192)',
        'rgb(54, 162, 235)',
        'rgb(153, 102, 255)',
        'rgb(63, 245, 57)',
        'rgb(159, 20, 193)']
    imaging_table = \
        pd.read_csv(
            imaging_table_data,
            skiprows=3,
            header=None,
            names=mod_headers,
            index_col=False)
    data = \
        imaging_table.groupby(['Lane', 'Tile']).\
        agg(np.mean).\
        reset_index()[['Lane', '% Occupied', '% Pass Filter']]
    dataset = list()
    for lane_id, l_data in data.groupby('Lane'):
        x = l_data['% Occupied'].values.tolist()
        y = l_data['% Pass Filter'].values.tolist()
        dataset.append({
            "x": x,
            "y": y,
            "lane_id": lane_id,
            "color": colors[lane_id-1]})
    return dataset

def get_interop_data_for_db(run_name, dump_file, runinfo_file, imaging_table_data=None):
    try:
        colors = [
            'rgb(255, 99, 132, 0.8)',
            'rgb(255, 159, 64, 0.8)',
            'rgb(255, 205, 86, 0.8)',
            'rgb(75, 192, 192, 0.8)',
            'rgb(54, 162, 235, 0.8)',
            'rgb(153, 102, 255, 0.8)',
            'rgb(63, 245, 57, 0.8)',
            'rgb(159, 20, 193, 0.8)']
        data = read_interop_data(dump_file)
        runinfoDf = read_runinfo_xml(runinfo_file)
        extractionDf = data.get("Extraction")
        intensity_data = get_intensity_data(extractionDf, colors)
        tile = data.get('Tile')
        q2030 = data.get('Q2030')
        extraction = data.get('Extraction')
        empiricalphasing = data.get('EmpiricalPhasing')
        error = data.get('Error')
        table_data = \
            get_table_data(tile, q2030, extraction, empiricalphasing, error, runinfoDf)
        surface_data = get_surface_data(tile)
        clusterCount_box_data, density_box_data = \
            get_cluster_and_density_counts(tile, colors)
        qByLane = data.get('QByLane')
        qscore_dist_data = get_qscore_bin_data(qByLane, colors)
        qscore_bar_plots = get_QScore_by_cycle_data(q2030, colors)
        occupied_data = ''
        if imaging_table_data is not None:
            occupied_data = \
                get_occupied_pass_filter(
                    imaging_table_data=imaging_table_data)
            occupied_data = json.dumps(occupied_data)
        json_data = {
            "run_name": run_name,
            "table_data": table_data,
            "flowcell_data": json.dumps(surface_data),
            "intensity_data": json.dumps(intensity_data),
            "cluster_count_data": json.dumps(clusterCount_box_data),
            "density_data": json.dumps(density_box_data),
            "qscore_bins_data": json.dumps(qscore_dist_data),
            "qsocre_cycles_data": json.dumps(qscore_bar_plots),
            "occupied_pass_filter": occupied_data}
        return json_data
    except:
        raise


def generate_data_dumps_and_create_json_for_db(
    run_id, run_path, output_dir, generate_imaging, interop_dumptext_exe, interop_imaging_tablet_exe):
    try:
        with tempfile.TemporaryDirectory() as temp_dir :
            if not os.path.exists(run_path):
                raise IOError('Run path {0} not found'.format(run_path))
            final_json_output = \
                os.path.join(output_dir, "{0}.json".format(run_id))
            if os.path.exists(final_json_output):
                raise IOError('Output file {0} already present'.format(final_json_output))
            dumptext_csv = \
                os.path.join(temp_dir, "{0}.csv".format(run_id))
            dumptext_cmd = \
                "{0} {1} > {2}".\
                    format(
                        interop_dumptext_exe,
                        run_path,
                        dumptext_csv)
            subprocess.check_call(dumptext_cmd, shell=True)
            imaging_csv = None
            if generate_imaging:
                imaging_csv = \
                    os.path.join(temp_dir, "{0}_imaging.csv".format(run_id))
                imaging_table_cmd = \
                    "{0} {1} > {2}".\
                        format(
                            interop_imaging_tablet_exe,
                            run_path,
                            imaging_csv)
                subprocess.check_call(imaging_table_cmd, shell=True)
            temp_json_output = \
                os.path.join(temp_dir, "{0}.json".format(run_id))
            os.makedirs(output_dir, exist_ok=True)
            json_data = \
                get_interop_data_for_db(
                    run_name=run_id,
                    dump_file=dumptext_csv,
                    runinfo_file=os.path.join(run_path, 'RunInfo.xml'),
                    imaging_table_data=imaging_csv)
            with open(temp_json_output, 'w') as fp:
                json.dump(json_data, fp)
            copy2(temp_json_output, final_json_output)
    except Exception as e:
        logging.error(e)
        raise
