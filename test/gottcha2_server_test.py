# -*- coding: utf-8 -*-
import os
import time
import unittest
from configparser import ConfigParser
import subprocess
import logging

from gottcha2.gottcha2Impl import gottcha2
from gottcha2.gottcha2Server import MethodContext
from gottcha2.authclient import KBaseAuth as _KBaseAuth

from installed_clients.WorkspaceClient import Workspace
from installed_clients.ReadsUtilsClient import ReadsUtils


class gottcha2Test(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        token = os.environ.get('KB_AUTH_TOKEN', None)
        config_file = os.environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('gottcha2'):
            cls.cfg[nameval[0]] = nameval[1]
        # Getting username from Auth profile for token
        authServiceUrl = cls.cfg['auth-service-url']
        auth_client = _KBaseAuth(authServiceUrl)
        user_id = auth_client.get_user(token)
        # WARNING: don't call any logging methods on the context object,
        # it'll result in a NoneType error
        cls.ctx = MethodContext(None)
        cls.ctx.update({'token': token,
                        'user_id': user_id,
                        'provenance': [
                            {'service': 'gottcha2',
                             'method': 'please_never_use_it_in_production',
                             'method_params': []
                             }],
                        'authenticated': 1})
        cls.wsURL = cls.cfg['workspace-url']
        cls.wsClient = Workspace(cls.wsURL)
        cls.serviceImpl = gottcha2(cls.cfg)
        cls.scratch = cls.cfg['scratch']
        cls.callback_url = os.environ['SDK_CALLBACK_URL']
        suffix = int(time.time() * 1000)
        cls.wsName = "test_ContigFilter_" + str(suffix)
        cls.ru = ReadsUtils(os.environ['SDK_CALLBACK_URL'])
        ret = cls.wsClient.create_workspace({'workspace': cls.wsName})  # noqa

    @classmethod
    def prepareTestData(cls):

        filename = os.path.join(cls.scratch, 'test.fastq')

        readsUtil = ReadsUtils.upload_reads(cls.callback_url)
        # cls.assembly_ref = readsUtil.({
        #     'file': {'path': filename},
        #     'workspace_name': cls.wsName,
        #     'assembly_name': 'TestAssembly'
        # })
    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')

    # NOTE: According to Python unittest naming rules test method names should start from 'test'. # noqa
    def test_params(self):
        # Prepare test objects in workspace if needed using
        # self.getWsClient().save_objects({'workspace': self.getWsName(),
        #                                  'objects': []})
        #
        # Run your method by
        # ret = self.getImpl().your_method(self.getContext(), parameters...)
        #
        # Check returned data with
        # self.assertEqual(ret[...], ...) or other unittest methods
        # read_upload_params = {'fwd_file': os.path.join('data', 'gottcha2', 'RefSeq90', 'test2.fastq'),
        #                       'sequencing_tech': 'Illumina',
        #                       'interleaved': 1,
        #                       'wsname': self.wsName,
        #                       'name': 'test.fastq'
        #                       }
        # reads_ref = self.ru.upload_reads(read_upload_params)['obj_ref']
        result = self.serviceImpl.run_gottcha2(self.ctx, {'workspace_name': self.wsName,
                                                       'input_refs': ['22852/10/1'],
                                                       'db_type': 'RefSeq-r90.cg.Viruses.species.fna',
                                                       'min_coverage': 0.005
                                                       })
        report_params = result[0]
        logging.info(f'{report_params}')
        # logging.info(result)
        # self.assertEqual(report_params['html_links'][0]['name'],
        #                  'default.krona.html')

    def test_gottcha(self):
        self.assertTrue(os.path.exists('/data/gottcha2/RefSeq90'))
        self.assertTrue(os.path.exists('/data/gottcha2/RefSeq90/RefSeq-r90.cg.Viruses.species.fna.mmi'))
        output_dir = os.path.join(self.scratch, 'test_gottcha')
        # 'sh lib/gottcha2/src/uge-gottcha2.sh -i test/data/test.fastq -o test/data/output -p testing -d test/data/RefSeq-r90.cg.Viruses.species.fna'
        cmd = ['/kb/module/lib/gottcha2/src/uge-gottcha2.sh', '-i', '/data/gottcha2/RefSeq90/test.fastq', '-o', output_dir, '-p',
               'testing', '-d', '/data/gottcha2/RefSeq90/RefSeq-r90.cg.Viruses.species.fna']
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(p.communicate())
        self.assertTrue(os.path.exists(os.path.join(output_dir, 'testing.summary.tsv')))
        self.assertTrue(os.path.exists(os.path.join(output_dir, 'testing.krona.html')))
        with open(os.path.join(output_dir, 'testing.summary.tsv'), 'r') as fp:
            logging.info('print summary')
            lines = fp.readlines()
            for line in lines:
                logging.info(line)
            self.assertTrue('Zaire ebolavirus' in lines[5])

