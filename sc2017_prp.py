#!/usr/bin/env python

import sys
import subprocess
from time import time, sleep
from elasticsearch import Elasticsearch, exceptions as es_exceptions
es = Elasticsearch(['atlas-kibana.mwt2.org:9200'],timeout=60)
index_name='sc2017'

def create_workload():
    
    # clean all
    try:
        es.indices.delete(index='sc2017')
    except:
        print("not there?")
    
    id=0
    
    l0 = [50,100,200]
    l1 = [0.0001,0.0002,0.0005]
    l2  = [0.00001, 0.00002, 0.00005]
    l3    = ['', '--no-attn']
    l4    = ['gamma.yaml', 'eplus.yaml', 'pion.yaml']
    for a in l0:
        for b in l1:
            for c in l2:
                for d in l3:
                    for e in l4:
                        doc={}
                        doc['created']=int(time()*1000)
                        doc['status']='created'
                        doc['training']={
                            'nb-epochs' : a,
                            'disc-lr' : b,
                            'gen-lr' : c,
                            'particle' : e,
                            'output_folder':'/data/CaloGAN/weights/'+str(id)
                        }
                        if d!='': doc['training']['options'] = d
                        doc['generator']={
                            'input_folder':'/data/CaloGAN/weights/'+str(id), 
                            'output_folder':'/data/CaloGAN/outputs/'+str(id), 
                            'epochs' : a,
                            'sets' : 10, 
                            'showers' : 100000
                        }
                        id+=1
#                         print(doc)
                        es.create(index=index_name, doc_type='doc', id=id, body=doc)


def get_training_job():
    my_query={
        "size": 1,
        "query":{ 
            "term": {"status":"created"} 
        }
    }

    res = es.search(index=index_name, body=my_query )
    res=res['hits']
    if res['total']==0:
        print('no training jobs at the moment.')
        return
    res_id=res['hits'][0]['_id']
    res=res['hits'][0]['_source']
    
    res['status']='training'
    res['start_training']=int(time()*1000)
    es.update(index=index_name, doc_type='doc', id=res_id, body={"doc":res})
    return (res_id, res)

def get_generating_job():
    my_query={
        "size": 1,
        "query":{ 
            "term": {"status":"trained"} 
        }
    }

    res = es.search(index=index_name, body=my_query )
    res=res['hits']
    if res['total']==0:
        print('no generating jobs at the moment.')
        return
    res_id=res['hits'][0]['_id']
    res=res['hits'][0]['_source']
    
    res['status']='generating'
    res['start_generating']=int(time()*1000)
    es.update(index=index_name, doc_type='doc', id=res_id, body={"doc":res})
    return (res_id, res)

def get_transfering_job():
    my_query={
        "size": 1,
        "query":{ 
            "term": {"status":"generated"} 
        }
    }

    res = es.search(index=index_name, body=my_query )
    res=res['hits']
    if res['total']==0:
        print('no transfering jobs at the moment.')
        return
    res_id=res['hits'][0]['_id']
    res=res['hits'][0]['_source']
    
    res['status']='transfering'
    res['start_transfering']=int(time()*1000)
    es.update(index=index_name, doc_type='doc', id=res_id, body={"doc":res})
    return (res_id, res)

def done_training(id):
    res={'status':'trained', 'end_training':int(time()*1000) }
    es.update(index=index_name, doc_type='doc', id=id, body={"doc":res})

def done_generating(id):
    res={'status':'generated', 'end_generating':int(time()*1000) }
    es.update(index=index_name, doc_type='doc', id=id, body={"doc":res})

def done_transfering(id):
    res={'status':'transfered', 'end_transfering':int(time()*1000) }
    es.update(index=index_name, doc_type='doc', id=id, body={"doc":res})

def test_flow():
    
    create_workload()

    (id, job) = get_training_job()
    print(id, job)
    sleep(5)
    done_training(id)

    sleep(15)

    (id, job) = get_generating_job()
    print(id, job)
    sleep(5)
    done_generating(id)

    sleep(15)

    (id, job) = get_transfering_job()
    print(id, job)
    sleep(5)
    done_transfering(id)

if __name__=='__main__':
    if len(sys.argv)!=2:
        print('Usage - sc2017.py <creator|trainer|generator|transporter>')
    else:
        print( 'this pod will be:', sys.argv[1] )
    
    role=sys.argv[1]
    if role=='creator':
        create_workload()
    elif role=='trainer':
        while (True):
            (id, job) = get_training_job()
            print('training job:',id, '\nsetting up:\n', job)
            op=job['training']
            
            print ('(re)create output directory')
            output = subprocess.check_output(['rm', '-rf', op['output_folder']])
            output = subprocess.check_output(['mkdir', '-p', op['output_folder']])

            options=[]
            options.append( '--output_folder=' + op['output_folder'] )
            options.append( '--nb-epochs=' + str(op['nb-epochs']) )
            options.append( '--disc-lr=' + str(op['disc-lr']) )
            options.append( '--gen-lr=' + str(op['gen-lr']) )
            if 'options' in op: 
                options.append( op['options'] )
            options.append( op['particle'] )
            print(options)
            output = subprocess.check_output(['/ML_platform_tests/tutorial/sc2017_prp/train.py'] + options)
            print(output)
            done_training(id)
            sleep(15)
    elif role=='generator':
        while (True):
            (id, job) = get_generating_job()
            print('generator job:',id, '\nsetting up:\n', job)
            g=job['generator']
            options=[g['input_folder'], g['output_folder'], str(g['epochs']), str(g['sets']), str(g['showers']) ]
            output = subprocess.check_output(['/ML_platform_tests/tutorial/sc2017_prp/generator.py']+options)
            print(output)
            done_generating(id)
            sleep(15)
    elif role=='transporter':
        while (True):
            (id, job) = get_transfering_job()
            print('transporter job:',id, '\nsetting up:\n', job)
            output = subprocess.check_output(['xrdcp ']+job['transfering_options'])
            print(output)
            done_transfering(id)
            sleep(15)