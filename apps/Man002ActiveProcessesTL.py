import os
import urllib.parse
from datetime import datetime

import dash_core_components as dcc
import dash_html_components as html
import dash_table_experiments as dt
import plotly.graph_objs as go
import pandas as pd
from dash.dependencies import Input, Output

from app import app, cache, cache_timeout

# Definitions: TL Apps and Renewals
# excludes jobs in Statuses More Information Required, Denied, Draft, Withdrawn, Approved
# excludes processes of Pay Fees, Provide More Information for Renewal, Amend License
# No completion date on processes

APP_NAME = os.path.basename(__file__)

print(APP_NAME)

time_categories = ["0-1 Day", "2-5 Days", "6-10 Days", "11 Days-1 Year", "Over 1 Year"]

@cache_timeout
@cache.memoize()
def query_data(dataset):
    from app import con
    with con() as con:
        if dataset == 'df_ind':
            sql = 'SELECT * FROM li_dash_activeproc_tl_ind'
        elif dataset == 'df_counts':
            sql = 'SELECT * FROM li_dash_activeproc_tl_counts'
        elif dataset == 'ind_last_ddl_time':
            sql = 'SELECT SCN_TO_TIMESTAMP(MAX(ora_rowscn)) last_ddl_time FROM LI_DASH_ACTIVEPROC_TL_IND'
        elif dataset == 'counts_last_ddl_time':
            sql = 'SELECT SCN_TO_TIMESTAMP(MAX(ora_rowscn)) last_ddl_time FROM LI_DASH_ACTIVEPROC_TL_COUNTS'
        df = pd.read_sql_query(sql=sql, con=con)
        if dataset == 'df_counts':
            # Make TIMESINCESCHEDULEDSTARTDATE a Categorical Series and give it a sort order
            df['TIMESINCESCHEDULEDSTARTDATE'] = pd.Categorical(df['TIMESINCESCHEDULEDSTARTDATE'], time_categories)
            df.sort_values(by='TIMESINCESCHEDULEDSTARTDATE', inplace=True)
    return df.to_json(date_format='iso', orient='split')

def dataframe(dataset):
    return pd.read_json(query_data(dataset), orient='split')

def update_layout():
    df_counts = dataframe('df_counts')
    counts_last_ddl_time = dataframe('counts_last_ddl_time')
    ind_last_ddl_time = dataframe('ind_last_ddl_time')

    processtype_options_unsorted = []
    for processtype in df_counts['PROCESSTYPE'].unique():
        processtype_options_unsorted.append({'label': str(processtype),'value': processtype})
    processtype_options_sorted = sorted(processtype_options_unsorted, key=lambda k: k['label'])

    licensetype_options_unsorted = [{'label': 'All', 'value': 'All'}]
    for licensetype in df_counts['LICENSETYPE'].unique():
        if str(licensetype) != "nan":
            licensetype_options_unsorted.append({'label': str(licensetype), 'value': licensetype})
    licensetype_options_sorted = sorted(licensetype_options_unsorted, key=lambda k: k['label'])

    return html.Div([
        html.H1(
            'Active Processes',
            style={'margin-top': '10px'}
        ),
        html.H1(
            '(Trade Licenses)',
            style={'margin-bottom': '50px'}
        ),
        html.Div([
            html.Div([
                html.P('Process Type'),
                dcc.Dropdown(
                    id='processtype-dropdown',
                    options=processtype_options_sorted,
                    multi=True
                ),
            ], className='four columns'),
            html.Div([
                html.P('License Type'),
                dcc.Dropdown(
                    id='licensetype-dropdown',
                    options=licensetype_options_sorted,
                    value='All',
                    searchable=True
                ),
            ], className='six columns'),
        ], className='dashrow filters'),
        html.Div([
            dcc.Graph(
                id='002TL-graph',
                config={
                    'displayModeBar': False
                },
                figure=go.Figure(
                    data=[
                        go.Bar(
                            x=df_counts[df_counts['JOBTYPE'] == 'Application']['TIMESINCESCHEDULEDSTARTDATE'],
                            y=df_counts[df_counts['JOBTYPE'] == 'Application']['PROCESSCOUNTS'],
                            name='Applications',
                            marker=go.bar.Marker(
                                color='rgb(55, 83, 109)'
                            )
                        ),
                        go.Bar(
                            x=df_counts[df_counts['JOBTYPE'] == 'Amend/Renew']['TIMESINCESCHEDULEDSTARTDATE'],
                            y=df_counts[df_counts['JOBTYPE'] == 'Amend/Renew']['PROCESSCOUNTS'],
                            name='Renewals/Amendments',
                            marker=go.bar.Marker(
                                color='rgb(26, 118, 255)'
                            )
                        )
                    ],
                    layout=go.Layout(
                        showlegend=True,
                        legend=go.layout.Legend(
                            x=.75,
                            y=1
                        ),
                        xaxis=dict(
                            autorange=True,
                            tickangle=30,
                            tickfont=dict(
                                size=11
                            )
                        ),
                        yaxis=dict(
                            title='Active Processes'
                        ),
                        margin=go.layout.Margin(l=40, r=0, t=40, b=100)
                    )
                )
            )
        ], style={'margin-left': 'auto', 'margin-right': 'auto', 'float': 'none'},
            className='nine columns'),
        html.P("Data last updated {}".format(counts_last_ddl_time['LAST_DDL_TIME'].iloc[0]), className = 'timestamp', style = {
        'text-align': 'center'}),
        html.Div([
            html.Div([
                html.Div([
                    dt.DataTable(
                        # Initialise the rows
                        rows=[{}],
                        filterable=True,
                        sortable=True,
                        selected_row_indices=[],
                        editable=False,
                        id='Man002ActiveProcessesTL-table'
                    )
                ], style={'text-align': 'center'}),
                html.Div([
                    html.A(
                        'Download Data',
                        id='Man002ActiveProcessesTL-download-link',
                        download='Man002ActiveProcessesTL.csv',
                        href='',
                        target='_blank',
                    )
                ], style={'text-align': 'right'}),
            ], style={'margin-top': '70px', 'margin-bottom': '50px'})
        ], className='dashrow'),
        html.P("Data last updated {}".format(ind_last_ddl_time['LAST_DDL_TIME'].iloc[0]), className = 'timestamp', style = {
            'text-align': 'center'}),
        html.Details([
            html.Summary('Query Description'),
            html.Div(
                'Incomplete processes (excluding "Pay Fees", "Provide More Information for Renewal", and "Amend License" '
                'processes) associated with trade license application or amend/renew jobs that dont\'t have statuses of "Approved", '
                '"Deleted", "Draft", "Withdrawn", "More Information Required", or '
                '"Denied" (i.e. have statuses of "In Review", "Payment Pending", '
                '"Submitted",  "Distribute", "Cancelled")')
        ])
    ])

layout = update_layout


def get_data_object(process_type, license_type):
    df_selected = dataframe('df_ind')
    if process_type is not None:
        if isinstance(process_type, str):
            df_selected = df_selected[df_selected['PROCESSTYPE'] == process_type]
        elif isinstance(process_type, list):
            if len(process_type) > 1:
                df_selected = df_selected[df_selected['PROCESSTYPE'].isin(process_type)]
            elif len(process_type) == 1:
                df_selected = df_selected[df_selected['PROCESSTYPE'] == process_type[0]]
    if license_type != "All":
        df_selected = df_selected[df_selected['LICENSETYPE'] == license_type]
    return df_selected.drop(['PROCESSID'], axis=1)

def update_counts_graph_data(process_type, license_type):
    df_counts_selected = dataframe('df_counts')
    if process_type is not None:
        if isinstance(process_type, str):
            df_counts_selected = df_counts_selected[df_counts_selected['PROCESSTYPE'] == process_type]
        elif isinstance(process_type, list):
            if len(process_type) > 1:
                df_counts_selected = df_counts_selected[df_counts_selected['PROCESSTYPE'].isin(process_type)]
            elif len(process_type) == 1:
                df_counts_selected = df_counts_selected[df_counts_selected['PROCESSTYPE'] == process_type[0]]
    if license_type != "All":
        df_counts_selected = df_counts_selected[df_counts_selected['LICENSETYPE'] == license_type]
    df_grouped = (df_counts_selected.groupby(by=['JOBTYPE', 'TIMESINCESCHEDULEDSTARTDATE'])['PROCESSCOUNTS']
                  .sum()
                  .reset_index())
    df_grouped['JOBTYPE'] = df_grouped['JOBTYPE'].astype(str)
    df_grouped['TIMESINCESCHEDULEDSTARTDATE'] = pd.Categorical(df_grouped['TIMESINCESCHEDULEDSTARTDATE'], time_categories)
    for time_cat in time_categories:
        if time_cat not in df_grouped[df_grouped['JOBTYPE'] == 'Application']['TIMESINCESCHEDULEDSTARTDATE'].values:
            df_missing_time_cat = pd.DataFrame([['Application', time_cat, 0]], columns=['JOBTYPE', 'TIMESINCESCHEDULEDSTARTDATE', 'PROCESSCOUNTS'])
            df_grouped = df_grouped.append(df_missing_time_cat, ignore_index=True)
    df_grouped['TIMESINCESCHEDULEDSTARTDATE'] = pd.Categorical(df_grouped['TIMESINCESCHEDULEDSTARTDATE'], time_categories)
    return df_grouped.sort_values(by='TIMESINCESCHEDULEDSTARTDATE')

@app.callback(
    Output('002TL-graph', 'figure'),
    [Input('processtype-dropdown', 'value'),
     Input('licensetype-dropdown', 'value')])
def update_graph(process_type, license_type):
    df_counts_updated = update_counts_graph_data(process_type, license_type)
    return {
        'data': [
            go.Bar(
                x=df_counts_updated[df_counts_updated['JOBTYPE'] == 'Application']['TIMESINCESCHEDULEDSTARTDATE'],
                y=df_counts_updated[df_counts_updated['JOBTYPE'] == 'Application']['PROCESSCOUNTS'],
                name='Applications',
                marker=go.bar.Marker(
                    color='rgb(55, 83, 109)'
                )
            ),
            go.Bar(
                x=df_counts_updated[df_counts_updated['JOBTYPE'] == 'Amend/Renew']['TIMESINCESCHEDULEDSTARTDATE'],
                y=df_counts_updated[df_counts_updated['JOBTYPE'] == 'Amend/Renew']['PROCESSCOUNTS'],
                name='Renewals/Amendments',
                marker=go.bar.Marker(
                    color='rgb(26, 118, 255)'
                )
            )
        ],
        'layout': go.Layout(
            showlegend=True,
            legend=go.layout.Legend(
                x=.75,
                y=1,
            ),
            xaxis=dict(
                autorange=True,
                tickangle=30,
                tickfont=dict(
                    size=11
                )
            ),
            yaxis=dict(
                title='Active Processes'
            ),
            margin=go.layout.Margin(l=40, r=0, t=40, b=100)
        )
    }

@app.callback(
    Output('Man002ActiveProcessesTL-table', 'rows'), 
    [Input('processtype-dropdown', 'value'),
     Input('licensetype-dropdown', 'value')])
def update_table(process_type, license_type):
    df = get_data_object(process_type, license_type)
    return df.to_dict('records')

@app.callback(
    Output('Man002ActiveProcessesTL-download-link', 'href'),
    [Input('processtype-dropdown', 'value'),
     Input('licensetype-dropdown', 'value')])
def update_download_link(process_type, license_type):
    df = get_data_object(process_type, license_type)
    csv_string = df.to_csv(index=False, encoding='utf-8')
    csv_string = "data:text/csv;charset=utf-8," + urllib.parse.quote(csv_string)
    return csv_string
