#!/usr/bin/env python

import sys
import subprocess
from time import time, sleep
from elasticsearch import Elasticsearch, exceptions as es_exceptions

es = Elasticsearch(['atlas-kibana.mwt2.org:9200'], timeout=60)
index_name = 'sc2017'


def create_workload():

    # clean all
    try:
        es.indices.delete(index='sc2017')
    except:
        print("not there?")

    id = 0
    l0 = [5, 50, 200]
    l1 = [0.0001, 0.0002, 0.0005]
    l2 = [0.00001, 0.00002, 0.00005]
    # l3 = ['', '--no-attn']
    l4 = ['gamma.yaml', 'eplus.yaml', 'pion.yaml']
    for a in l0:
        for b in l1:
            for c in l2:
                # for d in l3:
                for e in l4:
                    doc = {}
                    doc['created'] = int(time() * 1000)
                    doc['status'] = 'created'
                    doc['epochs'] = a
                    doc['training'] = {
                        'disc-lr': b,
                        'gen-lr': c,
                        'particle': e,
                        'output_folder': '/data-rook/CaloGAN/weights/' + str(id)
                    }
                    # if d != '':
                    #     doc['training']['options'] = d
                    doc['generator'] = {
                        'input_folder': '/data-rook/CaloGAN/weights/' + str(id),
                        'output_folder': '/data-rook/CaloGAN/outputs/' + str(id)
                    }
                    doc['generator_sets'] = 10
                    doc['generator_showers'] = 100000
                    doc['transferring_options'] = 'root://faxbox.usatlas.org:1094//faxbox2/user/ivukotic/outputs/' + str(id)

                    es.create(index=index_name, doc_type='doc', id=id, body=doc)
                    id += 1


def get_training_job():
    my_query = {
        "size": 1,
        "query": {"term": {"status": "created"}}
    }

    res = es.search(index=index_name, body=my_query)
    res = res['hits']
    if res['total'] == 0:
        print('no training jobs at the moment.')
        return
    res_id = res['hits'][0]['_id']
    res = res['hits'][0]['_source']

    res['status'] = 'training'
    res['start_training'] = int(time() * 1000)
    es.update(index=index_name, doc_type='doc', id=res_id, body={"doc": res})
    return (res_id, res)


def get_generating_job():
    my_query = {
        "size": 1,
        "query": {"term": {"status": "trained"}}
    }

    res = es.search(index=index_name, body=my_query)
    res = res['hits']
    if res['total'] == 0:
        print('no generating jobs at the moment.')
        return
    res_id = res['hits'][0]['_id']
    res = res['hits'][0]['_source']

    res['status'] = 'generating'
    res['start_generating'] = int(time() * 1000)
    es.update(index=index_name, doc_type='doc', id=res_id, body={"doc": res})
    return (res_id, res)


def get_transfering_job():
    my_query = {
        "size": 1,
        "query": {"term": {"status": "generated"}}
    }

    res = es.search(index=index_name, body=my_query)
    res = res['hits']
    if res['total'] == 0:
        print('no transfering jobs at the moment.')
        return
    res_id = res['hits'][0]['_id']
    res = res['hits'][0]['_source']

    res['status'] = 'transfering'
    res['start_transfering'] = int(time() * 1000)
    es.update(index=index_name, doc_type='doc', id=res_id, body={"doc": res})
    return (res_id, res)


def done_training(id):
    res = {'status': 'trained', 'end_training': int(time() * 1000)}
    es.update(index=index_name, doc_type='doc', id=id, body={"doc": res})


def done_generating(id):
    res = {'status': 'generated', 'end_generating': int(time() * 1000)}
    es.update(index=index_name, doc_type='doc', id=id, body={"doc": res})


def done_transfering(id):
    res = {'status': 'transfered', 'end_transfering': int(time() * 1000)}
    es.update(index=index_name, doc_type='doc', id=id, body={"doc": res})


def set_status(id, new_status):
    res = {'status': new_status}
    es.update(index=index_name, doc_type='doc', id=id, body={"doc": res})


def set_transferring_options(id):
    res = {'transferring_options': 'root://faxbox.usatlas.org:1094//faxbox2/user/ivukotic/outputs/' + str(id)}
    es.update(index=index_name, doc_type='doc', id=id, body={"doc": res})


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


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage - sc2017.py <creator|trainer|generator|transporter>')
    else:
        print('this pod will be:', sys.argv[1])

    role = sys.argv[1]
    if role == 'creator':
        print('start cleaning')
        output = subprocess.check_output(['rm', '-rf', '/data-rook/CaloGAN/weights'])
        output = subprocess.check_output(['rm', '-rf', '/data-rook/CaloGAN/outputs'])
        print('start creating workload')
        create_workload()
        print('done.')
    elif role == 'trainer':
        while (True):
            res = get_training_job()
            if not res:
                print('waiting...')
                sleep(120)
                continue
            (id, job) = res
            print('training job:', id, '\nsetting up:\n', job)
            op = job['training']

            print('(re)create output directory')
            output = subprocess.check_output(['rm', '-rf', op['output_folder']])
            output = subprocess.check_output(['mkdir', '-p', op['output_folder']])

            options = []
            options.append('--output_folder=' + op['output_folder'])
            options.append('--nb-epochs=' + str(job['epochs']))
            options.append('--disc-lr=' + str(op['disc-lr']))
            options.append('--gen-lr=' + str(op['gen-lr']))
            if 'options' in op:
                options.append(op['options'])
            options.append(op['particle'])
            print(options)
            output = subprocess.check_output(['/ML_platform_tests/tutorial/sc2017_prp/train.py'] + options)
            print(output)
            done_training(id)
            sleep(15)
    elif role == 'generator':
        while (True):
            res = get_generating_job()
            if not res:
                print('waiting...')
                sleep(120)
                continue
            (id, job) = res
            print('generator job:', id, '\nsetting up:\n', job)
            g = job['generator']
            output = subprocess.check_output(['rm', '-rf', g['output_folder']])
            output = subprocess.check_output(['mkdir', '-p', g['output_folder']])
            options = [g['input_folder'], g['output_folder'], str(job['epochs']), str(job['generator_sets']), str(job['generator_showers'])]
            print(options)
            output = subprocess.check_output(['/ML_platform_tests/tutorial/sc2017_prp/generator.py'] + options)
            print(output)
            done_generating(id)
            sleep(15)
    elif role == 'transporter':
        while (True):
            res = get_transfering_job()
            if not res:
                print('waiting...')
                sleep(120)
                continue
            (id, job) = res
            print('transporter job:', id, '\nsetting up:\n', job)
            output_folder = job['generator']['output_folder']
            output = subprocess.check_output(['xrdcp', '-r', output_folder, job['transferring_options']])
            print(output)
            done_transfering(id)
            sleep(60)
