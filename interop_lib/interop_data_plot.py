import os,re
import pandas as pd
from collections import defaultdict
import seaborn as sns
import iplotter
from IPython.display import HTML

def read_interop_data(filepath):
  """
  This function reads a dump file generated by interop_dumptext tool and returns a list of Pandas dataframe
  
  :param filepath: A interop dumptext output path
  :returns: A list of Pandas dataframes
  
    * Tile
    * Q2030
    * Extraction
    * Error
    * EmpiricalPhasing
    * CorrectedInt
    * QByLane
    
  """
  try:
    if not os.path.exists(filepath):
      raise IOError('File {0} not found'.format(filepath))
    data = defaultdict(list)
    header = None
    data_header = None
    with open(filepath,'r') as fp:
      for line in fp:
        line = line.strip()
        if line.startswith('#'):
          if line.startswith('# Version') or \
             line.startswith('# Column Count') or \
             line.startswith('# Bin Count') or \
             line.startswith('# Channel Count'):
            pass
          else:
            header=line.strip('# ').split(',')[0]
        else:
          if header is not None:
            if 'Lane' in line.split(','):
              data_header = line.split(',')
              continue
            if data_header is not None:
              data[header].append(dict(zip(data_header,line.split(','))))
    for key in ('CorrectedInt','Tile','Q2030','Extraction','Error','EmpiricalPhasing','QByLane'):
      if key not in data:
        raise KeyError('No entry for {0} found in interop dump'.format(key))
    tile = pd.DataFrame(data.get('Tile'))
    q2030 = pd.DataFrame(data.get('Q2030'))
    extraction = pd.DataFrame(data.get('Extraction'))
    error = pd.DataFrame(data.get('Error'))
    correctedInt = pd.DataFrame(data.get('CorrectedInt'))
    empiricalPhasing = pd.DataFrame(data.get('EmpiricalPhasing'))
    qByLane = pd.DataFrame(data.get('QByLane'))
    return tile,q2030,extraction,error,empiricalPhasing,correctedInt,qByLane
  except Exception as e:
    raise ValueError('Failed to extract data from interop dump, error:{0}'.format(e))

def read_runinfo_xml(runInfoXml_path):
  """
  A function for reading RunInfo.xml file from Illumina sequencing run and returns data as Pandas DataFrame
  
  :param runInfoXml_path: Filepath for RunInfo.xml
  :returns: A Pandas dataframe containing the run configuration data
  """
  try:
    if not os.path.exists(runInfoXml_path):
      raise IOError('File {0} not found'.format(runInfoXml_path))
    pattern = re.compile(r'<Read Number=\"(\d)\" NumCycles=\"(\d+)\" IsIndexedRead=\"(Y|N)\" />')
    read_info = list()
    with open(runInfoXml_path,'r') as fp:
      for line in fp:
        line = line.strip()
        if line.startswith('<Read Number'):
          read_info.append(line)
          read_start = 0
          reads_stat = list()
          for i in read_info:
            if re.match(pattern,i):
              read_number,numcycle,index_read = re.match(pattern,i).groups()
              reads_stat.append({
                'read_id':int(read_number),
                'cycles':int(numcycle),
                'start_cycle':int(read_start),
                'index_read':index_read})
              read_start += int(numcycle)
    reads_stat = pd.DataFrame(reads_stat)
    reads_stat['read_id'] = reads_stat['read_id'].astype(int)
    return reads_stat
  except Exception as e:
    raise ValueError('Failed to read RunInfo.xml for sequencing run, error: {0}'.format(e))

def extract_read_data_from_tileDf(tileDf):
  try:
    read_data = list()
    for read_id,r_data in tileDf.groupby('Read'):
      for lane_id,l_data in r_data.groupby('Lane'):
        read_count = l_data['ClusterCount'].astype(float).sum()
        read_count = int(read_count)/1000000
        read_count_pf = l_data['ClusterCountPF'].astype(float).sum()
        read_count_pf = int(read_count_pf)/1000000
        density_count = l_data['Density'].astype(float).mean()
        density_count = int(density_count)/1000
        pct_cluster_count_pf = '{0:.2f}'.format(int(read_count_pf)/int(read_count))
        read_data.append({
          'read_id':read_id,
          'lane_id':lane_id,
          'density':'{:.2f}'.format(density_count),
          'read_count':'{:.2f}'.format(read_count),
          'read_count_pf':'{:.2f}'.format(read_count_pf),
          'cluster_pf':pct_cluster_count_pf})
    read_data = pd.DataFrame(read_data)
    read_data['read_id'] = read_data['read_id'].astype(int)
    read_data['lane_id'] = read_data['lane_id'].astype(int)
    return read_data
  except Exception as e:
    raise ValueError('Failed to extract data from TileDf, error: {0}'.format(e))

def extract_yield_data_from_q2030Df(q2030Df,runinfoDf):
  try:
    yield_data = list ()
    q2030Df['Lane'] = q2030Df['Lane'].astype(int)
    q2030Df['Cycle'] = q2030Df['Cycle'].astype(int)
    for lane_id,l_data in q2030Df.groupby('Lane'):
      for read_entry in runinfoDf.to_dict(orient='records'):
        read_id = read_entry.get('read_id')
        start_cycle = int(read_entry.get('start_cycle'))
        total_cycle = int(read_entry.get('cycles'))
        finish_cycle = start_cycle + total_cycle
        r_q30 = l_data[(l_data['Cycle'] > start_cycle) & (l_data['Cycle'] < finish_cycle)]['Q30'].astype(int).fillna(0).sum()
        r_t = l_data[(l_data['Cycle'] > start_cycle) & (l_data['Cycle'] < finish_cycle)]['Total'].astype(int).fillna(0).sum()
        r_pct = '{:.2f}'.format(int(r_q30)/int(r_t) * 100)
        r_yield = '{:.2f}'.format(int(r_t)/1000000000)
        yield_data.append({
          'lane_id':lane_id,
          'read_id':read_id,
          'q30_pct':r_pct,
          'yield':r_yield
        })
    yield_data = pd.DataFrame(yield_data)
    yield_data['read_id'] = yield_data['read_id'].astype(int)
    yield_data['lane_id'] = yield_data['lane_id'].astype(int)
    return yield_data
  except Exception as e:
    raise ValueError('Failed to extract data from q2030Df, error: {0}'.format(e))

def get_extraction_data_from_extractionDf(extractionDf,runinfoDf):
  try:
    extractionDf['Lane'] = extractionDf['Lane'].astype(int)
    extractionDf['Cycle'] = extractionDf['Cycle'].astype(int)
    extractionDf['MaxIntensity_A'] = extractionDf['MaxIntensity_A'].astype(int)
    extractionDf['MaxIntensity_T'] = extractionDf['MaxIntensity_T'].astype(int)
    extractionDf['MaxIntensity_G'] = extractionDf['MaxIntensity_G'].astype(int)
    extractionDf['MaxIntensity_C'] = extractionDf['MaxIntensity_C'].astype(int)
    extraction_data = list()
    for lane_id,l_data in extractionDf.groupby('Lane'):
      for read_entry in runinfoDf.to_dict(orient='records'):
        read_id = read_entry.get('read_id')
        start_cycle = int(read_entry.get('start_cycle')) + 1
        mean_a = l_data[l_data['Cycle']==start_cycle]['MaxIntensity_A'].mean()
        extraction_data.append({
          'lane_id':lane_id,
          'read_id':read_id,
          'intensity_c1':'{:.2f}'.format(mean_a)})
    extraction_data = pd.DataFrame(extraction_data)
    extraction_data['lane_id'] =  extraction_data['lane_id'].astype(int)
    extraction_data['read_id'] =  extraction_data['read_id'].astype(int)
    return extraction_data
  except Exception as e:
    raise ValueError('Failed to get data from extractionDf, error: {0}'.format(e))

def get_data_from_errorDf(errorDf,runinfoDf):
  try:
    errorDf['Lane'] = errorDf['Lane'].astype(int)
    errorDf['Cycle'] = errorDf['Cycle'].astype(int)
    error_data = list()
    for lane_id,l_data in errorDf.groupby('Lane'):
      for read_entry in runinfoDf.to_dict(orient='records'):
        read_id = read_entry.get('read_id')
        start_cycle = int(read_entry.get('start_cycle'))
        total_cycle = int(read_entry.get('cycles'))
        finish_cycle = start_cycle + total_cycle
        error_cycles = l_data[(l_data['Cycle'] > start_cycle) & (l_data['Cycle'] < finish_cycle)]['Cycle'].drop_duplicates().count()
        error_data.append({
          'lane_id':lane_id,
          'read_id':read_id,
          'error_cycles':error_cycles})
    error_data = pd.DataFrame(error_data)
    error_data['lane_id'] = error_data['lane_id'].astype(int)
    error_data['read_id'] = error_data['read_id'].astype(int)
    return error_data
  except Exception as e:
    raise ValueError('Failed to get data from errorDf, error: {0}'.format(e))

def get_summart_stats(tileDf,q2030Df,extractionDf,errorDf,runinfoDf):
  try:
    read_data = extract_read_data_from_tileDf(tileDf=tileDf)
    yield_data = extract_yield_data_from_q2030Df(q2030Df=q2030Df,runinfoDf=runinfoDf)
    extraction_data = get_extraction_data_from_extractionDf(extractionDf=extractionDf,runinfoDf=runinfoDf)
    error_data = get_data_from_errorDf(errorDf=errorDf,runinfoDf=runinfoDf)
    merged_data = \
      yield_data.\
        merge(read_data,how='left',on=['read_id','lane_id']).\
        merge(runinfoDf,how='left',on='read_id').\
        merge(extraction_data,how='left',on=['lane_id','read_id']).\
        merge(error_data,how='left',on=['lane_id','read_id']).\
        fillna(0)
    return merged_data
  except Exception as e:
    raise ValueError('Failed to get summary stats, error: {0}'.format(e))

def plot_intensity_data(correctedIntDf,color_palette='Spectral_r'):
  try:
    if not isinstance(correctedIntDf,pd.DataFrame):
      raise TypeError('Expecting a pandas dataframe, got {0}'.format(type(correctedIntDf)))
    for i in ('Lane','Cycle','CalledIntensity_A','CalledIntensity_T','CalledIntensity_G','CalledIntensity_C'):
      if i not in correctedIntDf.columns:
        raise KeyError('Missing required key {0} from correctedIntDf'.format(i))
    correctedIntDf['Lane'] = correctedIntDf['Lane'].astype(int)
    correctedIntDf['Cycle'] = correctedIntDf['Cycle'].astype(int)
    correctedIntDf['CalledIntensity_A'] = correctedIntDf['CalledIntensity_A'].astype(float)
    correctedIntDf['CalledIntensity_T'] = correctedIntDf['CalledIntensity_T'].astype(float)
    correctedIntDf['CalledIntensity_G'] = correctedIntDf['CalledIntensity_G'].astype(float)
    correctedIntDf['CalledIntensity_C'] = correctedIntDf['CalledIntensity_C'].astype(float)
    formatted_data = list()
    intA_data = list()
    intT_data = list()
    intG_data = list()
    intC_data = list()
    for lane_id,l_data in correctedIntDf.groupby('Lane'):
      for cycle,c_data in l_data.groupby('Cycle'):
        formatted_data.append({
          'Lane':lane_id,
          'Cycle':cycle,
          'CalledIntensity_A': c_data['CalledIntensity_A'].median(),
          'CalledIntensity_T': c_data['CalledIntensity_T'].median(),
          'CalledIntensity_G': c_data['CalledIntensity_G'].median(),
          'CalledIntensity_C': c_data['CalledIntensity_C'].median()
        })
    formatted_data = pd.DataFrame(formatted_data)
    for lane_id,l_data in formatted_data.groupby('Lane'):
      labels = l_data.sort_values('Cycle').set_index('Cycle').index
      int_A = l_data.sort_values('Cycle').set_index('Cycle')['CalledIntensity_A'].values
      int_T = l_data.sort_values('Cycle').set_index('Cycle')['CalledIntensity_T'].values
      int_G = l_data.sort_values('Cycle').set_index('Cycle')['CalledIntensity_G'].values
      int_C = l_data.sort_values('Cycle').set_index('Cycle')['CalledIntensity_C'].values
      intA_data.append([lane_id,labels,int_A])
      intT_data.append([lane_id,labels,int_T])
      intG_data.append([lane_id,labels,int_G])
      intC_data.append([lane_id,labels,int_C])
    colors = sns.color_palette(color_palette,8,as_cmap=False).as_hex()
    datasetA = list()
    for entry,color in zip(intA_data,colors):
      (lane_id,labels,int_A) = entry
      datasetA.append({
        "label": "Lane {0}".format(lane_id),
        "data": list(int_A),
        "type": "line",
        "fill":False,
        "pointBorderColor":"transparent",
        "borderColor":color,
        "lineTension":0
      })
    dataA = {
      "datasets":datasetA,
      "labels": list(labels)}
    chart_jsA = iplotter.ChartJSPlotter()
    datasetT = list()
    for entry,color in zip(intT_data,colors):
      (lane_id,labels,int_T) = entry
      datasetT.append({
        "label": "Lane {0}".format(lane_id),
        "data": list(int_T),
        "type": "line",
        "fill":False,
        "pointBorderColor":"transparent",
        "borderColor":color,
        "lineTension":0
      })
    dataT = {
      "datasets":datasetT,
      "labels": list(labels)}
    chart_jsT = iplotter.ChartJSPlotter()
    datasetG = list()
    for entry,color in zip(intG_data,colors):
      (lane_id,labels,int_G) = entry
      datasetG.append({
        "label": "Lane {0}".format(lane_id),
        "data": list(int_G),
        "type": "line",
        "fill":False,
        "pointBorderColor":"transparent",
        "borderColor":color,
        "lineTension":0
      })
    dataG = {
      "datasets":datasetG,
      "labels": list(labels)}
    chart_jsG = iplotter.ChartJSPlotter()
    datasetC = list()
    for entry,color in zip(intC_data,colors):
      (lane_id,labels,int_C) = entry
      datasetC.append({
        "label": "Lane {0}".format(lane_id),
        "data": list(int_C),
        "type": "line",
        "fill":False,
        "pointBorderColor":"transparent",
        "borderColor":color
      })
    dataC = {
      "datasets":datasetC,
      "labels": list(labels)}
    chart_jsC = iplotter.ChartJSPlotter()
    optionsA = {
      "animation": {
        "duration": 0
      },
      "title": {
        "display": True,
        "text": 'Intensity plot of base A',
        "fontSize":16
        },
        "scales": {
          "yAxes":[{
            "scaleLabel":{
              "display":True,
              "labelString":"Intensity values"
            }
          }],
          "xAxes":[{
            "scaleLabel":{
              "display":True,
              "labelString":"Cycles"
            }
          }]
        }
    }
    optionsT = {
      "animation": {
        "duration": 0
      },
      "title": {
        "display": True,
        "text": 'Intensity plot of base T',
        "fontSize":16
        },
        "scales": {
          "yAxes":[{
            "scaleLabel":{
              "display":True,
              "labelString":"Intensity values"
            }
          }],
          "xAxes":[{
            "scaleLabel":{
              "display":True,
              "labelString":"Cycles"
            }
          }]
        }
    }
    optionsG = {
      "animation": {
        "duration": 0
      },
      "title": {
        "display": True,
        "text": 'Intensity plot of base G',
        "fontSize":16
        },
        "scales": {
          "yAxes":[{
            "scaleLabel":{
              "display":True,
              "labelString":"Intensity values"
            }
          }],
          "xAxes":[{
            "scaleLabel":{
              "display":True,
              "labelString":"Cycles"
            }
          }]
        }
    }
    optionsC = {
      "animation": {
        "duration": 0
      },
      "title": {
        "display": True,
        "text": 'Intensity plot of base C',
        "fontSize":16
        },
        "scales": {
          "yAxes":[{
            "scaleLabel":{
              "display":True,
              "labelString":"Intensity values"
            }
          }],
          "xAxes":[{
            "scaleLabel":{
              "display":True,
              "labelString":"Cycles"
            }
          }]
        }
    }
    return chart_jsA.plot(dataA,options=optionsA,chart_type="line", w=1000, h=600),\
           chart_jsT.plot(dataT,options=optionsT,chart_type="line", w=1000, h=600),\
           chart_jsG.plot(dataG,options=optionsG,chart_type="line", w=1000, h=600),\
           chart_jsC.plot(dataC,options=optionsC,chart_type="line", w=1000, h=600)
  except Exception as e:
    raise ValueError('Failed to generate intensity plots, error: {0}'.format(e))

def get_box_plots(tilesDf,color_palette='Spectral_r',width=800,height=600):
  """
  A function for plotting Boxplot for the entries from interop data
  
  :param tilesDf: A Pandas dataframe containing the Tiles data
  :param color_palette: Seaborn color palette name, default 'Spectral_r'
  :param width: Plot width, default 800
  :param height: Plot height, default 600
  :returns: A list of IPythondisplay.HTML objects containing the following boxplots

  * ClusterCount
  * Density

  """
  try:
    if not isinstance(tilesDf,pd.DataFrame):
      raise TypeError('Expecting a Pandas.DataFrame and got : {0}'.format(type(tilesDf)))
    if 'ClusterCountPF' not in tilesDf or \
       'ClusterCount' not in tilesDf or \
       'Density' not in tilesDf or \
       'DensityPF' not in tilesDf:
      raise KeyError('Missing required key for box plots')
    colors = sns.color_palette(color_palette,8,as_cmap=False).as_hex()
    tilesDf.dropna(inplace=True)
    tilesDf['ClusterCountPF'] = tilesDf['ClusterCountPF'].astype(float)
    tilesDf['ClusterCount'] = tilesDf['ClusterCount'].astype(float)
    tilesDf['Density'] = tilesDf['Density'].astype(float)
    tilesDf['DensityPF'] = tilesDf['DensityPF'].astype(float)
    tilesDf['Lane'] = tilesDf['Lane'].astype(int)
    clusterCount_box_data = list()
    density_box_data = list()
    for lane_id,l_data in tilesDf.groupby('Lane'):
      clusterCount_box_data.extend([{
        "y":list(l_data['ClusterCount'].values),
        "type": 'box',
        "name": 'Lane {0}'.format(lane_id),
        "marker": {
          "color": colors[lane_id-1]
        },
        "boxpoints": 'Outliers'
      },{
        "y":list(l_data['ClusterCountPF'].values),
        "type": 'box',
        "name": 'Lane {0}'.format(lane_id),
        "marker": {
          "color": colors[lane_id-1]
        },
        "boxpoints": 'Outliers'
      }])
      density_box_data.extend([{
        "y":list(l_data['Density'].values),
        "type": 'box',
        "name": 'Lane {0}'.format(lane_id),
        "marker": {
          "color": colors[lane_id-1]
        },
        "boxpoints": 'Outliers'
      },{
        "y":list(l_data['DensityPF'].values),
        "type": 'box',
        "name": 'Lane {0}'.format(lane_id),
        "marker": {
          "color": colors[lane_id-1]
        },
        "boxpoints": 'Outliers'
      }])
    clusterCount_layout = {
      "title": 'ClusterCount'
    }
    density_layout = {
      "title": 'Density'
    }
    clusterCount_plotter = iplotter.PlotlyPlotter()
    density_plotter = iplotter.PlotlyPlotter()
    return clusterCount_plotter.plot(clusterCount_box_data, layout=clusterCount_layout, w=width, h=height),\
           density_plotter.plot(density_box_data, layout=density_layout, w=width, h=height)
  except Exception as e:
    raise ValueError('Failed to prepare data for boxplots, error: {0}'.format(e))

def get_qscore_distribution_plots(qByLaneDf,color_palette='Spectral_r',width=800,height=400):
  try:
    key_cols = ['Bin_1', 'Bin_2', 'Bin_3', 'Bin_4', 'Bin_5', 'Bin_6', 'Bin_7']
    if not isinstance(qByLaneDf,pd.DataFrame):
      raise TypeError('Expecting a Pandas DataFrame and got {0}'.format(type(qByLaneDf)))
    for i in ('Lane','Bin_1', 'Bin_2', 'Bin_3', 'Bin_4', 'Bin_5', 'Bin_6', 'Bin_7'):
      if i not in qByLaneDf.columns:
        raise KeyError('Key column {0} not found in QByLane Df')
    qByLaneDf.fillna(0,inplace=True)
    qByLane_filt = qByLaneDf[qByLaneDf['Lane'].isin(['0','1','2','3','4','5','6','7','8'])].copy()
    qByLane_filt = qByLane_filt.applymap(lambda x: int(x))
    colors = sns.color_palette(color_palette,8,as_cmap=False).as_hex()
    max_q30_line = \
      int(qByLane_filt.groupby('Lane').agg('mean')['Bin_7'].max()) + 10000
    qscore_dist_data = list()
    for lane_id,l_data in qByLane_filt.groupby('Lane'):
      lane_id = int(lane_id)
      qscore_dist_data.append({
        "label": 'Lane {0}'.format(lane_id),
        "data": list(l_data[key_cols].mean().values),
        "backgroundColor":colors[lane_id - 1]
      })
    qscore_dist_data.append({
      "type":"line",
      "data":[
        {"y":None},
        {"y":None},
        {"y":None},
        {"y":None},
        {"y":max_q30_line},
        {"y":max_q30_line},
        {"y":max_q30_line}],
      "backgroundColor":"rgba(54, 162, 235, 0.3)",
      "borderColor":"transparent",
      "pointBorderColor":"transparent",
      "pointBackgroundColor":"transparent",
      "legend": { "display": False },
      "fill":'-1',
      "label":"Q30"
    })
    data = {
      "datasets": qscore_dist_data,
      "labels": key_cols
    }
    options = {
      "animation": {
        "duration": 0
      },
      "legend":{
        "display": True
      },
      "title": {
        "display": True,
        "text": 'QScore distribution plot',
        "fontSize":16
        },
        "scales": {
          "yAxes":[{
            "scaleLabel":{
              "display":True,
              "labelString":"Mean score values"
            }
          }],
          "xAxes":[{
            "scaleLabel":{
              "display":True,
              "labelString":"Lanes"
            }
          }]
        }
    }
    chart_js = iplotter.ChartJSPlotter()
    return chart_js.plot(data,options=options,chart_type="bar", w=width, h=height)
  except Exception as e:
    raise ValueError('Failed to get qscore plot, error: {0}'.format(e))

def get_qscore_bar_plots(q2030Df,color_palette='Spectral_r',width=1000,height=400):
  try:
    if not isinstance(q2030Df,pd.DataFrame):
      raise TypeError('Expecting a Pandas Dataframe and got {0}'.format(type(q2030Df)))
    for i in ('Lane','Tile','Cycle','MedianQScore'):
      if i not in q2030Df.columns:
        raise KeyError('Missing key column {0} in Q2030 df'.format(i))
    q2030Df['Lane'] = q2030Df['Lane'].astype(int)
    q2030Df['Cycle'] = q2030Df['Cycle'].astype(int)
    q2030Df['MedianQScore'] = q2030Df['MedianQScore'].astype(int)
    q2030Df['MedianQScore'] = \
      pd.np.where(q2030Df['MedianQScore'] > 50,0,q2030Df['MedianQScore'])
    q2030Df['Tile'] = q2030Df['Tile'].astype(int)
    qscore_bar_plots = list()
    colors = sns.color_palette(color_palette,8,as_cmap=False).as_hex()
    for lane_id,l_data in q2030Df.groupby('Lane'):
      lane_id = int(lane_id)
      dataset = list(l_data.groupby('Cycle')['MedianQScore'].mean().values)
      #dataset = [int(i) if i < 50 else 0 for i in dataset]
      labels = list(l_data.groupby('Cycle')['MedianQScore'].mean().index)
      data = {
        "datasets": [{
          "label": 'Lane {0}'.format(lane_id),
          "data": dataset,
          "backgroundColor":colors[lane_id-1],
        }],
        "labels": labels
      }
      options = {
      "animation": {
        "duration": 0
      },
      "title": {
        "display": True,
        "text": 'QScore distribution bar plot lane {0}'.format(lane_id),
        "fontSize":16
        },
        "scales": {
          "yAxes":[{
            "ticks":{
              "min":0,
              "max":45,
            },
            "scaleLabel":{
              "display":True,
              "labelString":"Mean QScore value"
            }
          }],
          "xAxes":[{
            "scaleLabel":{
              "display":True,
              "labelString":"Cycles"
            }
          }]
        }
    }
      chart_js = iplotter.ChartJSPlotter()
      qscore_bar_plots.append(chart_js.plot(data,options=options,chart_type="bar", w=width, h=height))
    return qscore_bar_plots
  except Exception as e:
    raise ValueError('Failed to get qscore heatmap, error: {0}'.format(e))

def color_numeric_column_by_value(s,target_column,threshold,good_color='green',bad_color='red'):
  try:
    color_list = list()
    if target_column not in list(s.keys()):
      raise KeyError('column {0} not found in series'.format(target_column))
    for c in list(s.keys()):
      if c==target_column:
        if float(s[c]) > float(threshold):
          color_list.append('color:{0}'.format(good_color))
        else:
          color_list.append('color:{0}'.format(bad_color))
      else:
        color_list.append('')
    return color_list
  except Exception as e:
    raise ValueError('Failed to color {0} column, error: {1}'.format(target_column,e))

def summary_report_and_plots_for_interop_dump(interop_dump,runInfoXml_path):
  try:
    (tile,q2030,extraction,error,empiricalPhasing,correctedInt,qByLane) = \
      read_interop_data(filepath=interop_dump)
    runinfoDf = read_runinfo_xml(runInfoXml_path)
    merged_data = \
      get_summart_stats(
        tileDf=tile,
        q2030Df=q2030,
        extractionDf=extraction,
        errorDf=error,
        runinfoDf=runinfoDf)
    merged_data.columns = [c.capitalize().replace("_"," ") for c in merged_data.columns]
    merged_data_html = \
      HTML(
        merged_data.style.apply(
          lambda s: color_numeric_column_by_value(s,target_column='Q30 pct',threshold=90.0),
          axis=1,).\
        hide_index().render())
    (intensityA_plot,intensityT_plot,intensityG_plot,intensityC_plot) = \
      plot_intensity_data(correctedIntDf=correctedInt)
    (clusterCount_plot,density_plot) = \
      get_box_plots(tilesDf=tile)
    qscore_distribution_plot = \
      get_qscore_distribution_plots(qByLaneDf=qByLane)
    qscore_bar_plots = \
      get_qscore_bar_plots(q2030Df=q2030)
    return merged_data_html,intensityA_plot,intensityT_plot,intensityG_plot,intensityC_plot,\
           clusterCount_plot,density_plot,qscore_distribution_plot,qscore_bar_plots
  except Exception as e:
    raise ValueError('Failed to get report and plots for interop, error: {0}'.format(e))

