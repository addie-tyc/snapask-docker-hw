from airflow.models import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.mysql.operators.mysql import MySqlOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook
from bs4 import BeautifulSoup as BS

from datetime import datetime, timedelta
import requests
import json


default_args = {
    'owner': 'addie chung',
    'depends_on_past': False,
    'start_date': datetime.utcnow(),
    'email': 'addiechung.tyc@gmail.com',
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(seconds=50),
    'execution_timeout': timedelta(minutes=5),
    'provide_context': True
}


dag = DAG(
    dag_id='crawl_snapask_dag',
    description='Get tutors info from https://snapask.com/zh-tw/tutors',
    default_args=default_args,
    schedule_interval='0 0 * * *'
)


def crawl_snapask():
    data = []
    i = 1
    id_set = set()
    while len(data) < 100:
        url = f"https://api.snapask.co/api/v3/web/tutor_list?region_name=tw&filter_name=&page={i}&lang=zh-TW"
        r = requests.get(url)
        tutor_list = json.loads(r.text)["data"]["tutors"]
        for j in range(len(tutor_list)):
            tutor_list[j]["top_answered_subjects"] = ",".join(tutor_list[j]["top_answered_subjects"])
            if tutor_list[j]["id"] not in id_set:
                data.append(tutor_list[j])
                id_set.add(tutor_list[j]["id"])
        i += 1

    sql_hook = MySqlHook(mysql_conn_id="RDS-snapask")
    conn = sql_hook.get_conn()
    conn.ping()
    cur = conn.cursor()
    cur.executemany('''
                    INSERT INTO tutor
                    (id, first_name, last_name, username, display_name, 
                    profile_pic_url, school, rating, answered_count, top_answered_subjects)
                    VALUES(%(id)s,  %(first_name)s,  %(last_name)s,  %(username)s,  %(display_name)s,  
                           %(profile_pic_url)s,  %(school)s,  %(rating)s,  %(answered_count)s,  %(top_answered_subjects)s)
                    ON DUPLICATE KEY UPDATE first_name = VALUES(first_name),
                                            last_name = VALUES(last_name), 
                                            username = VALUES(username), 
                                            display_name = VALUES(display_name), 
                                            profile_pic_url = VALUES(profile_pic_url), 
                                            school = VALUES(school), 
                                            rating = VALUES(rating), 
                                            answered_count = VALUES(answered_count), 
                                            top_answered_subjects = VALUES(top_answered_subjects);
                    ''', data)
    conn.commit()
    conn.close()


crawl_snapask_task = PythonOperator(
    task_id='crawl_snapask',
    python_callable=crawl_snapask,
    dag=dag
)

update_elite_tutor_task = MySqlOperator(
    task_id='update_elite_tutor',
    mysql_conn_id='RDS-snapask',
    sql='''
        INSERT INTO elite_tutor
        (id, first_name, last_name, username, display_name, 
        profile_pic_url, school, rating, answered_count, top_answered_subjects)
        SELECT * FROM tutor
         WHERE answered_count > 100 AND rating > 4.8
            ON DUPLICATE KEY UPDATE first_name = tutor.first_name,
                                    last_name = tutor.last_name, 
                                    username = tutor.username, 
                                    display_name = tutor.display_name, 
                                    profile_pic_url = tutor.profile_pic_url, 
                                    school = tutor.school, 
                                    rating = tutor.rating, 
                                    answered_count = tutor.answered_count, 
                                    top_answered_subjects = tutor.top_answered_subjects;
        ''',
    autocommit=True,
    dag=dag
)

crawl_snapask_task >> update_elite_tutor_task
