import os
from unittest import mock
import pytest


# pylint: disable=redefined-outer-name

@pytest.fixture()
def config_data_sample():
    """
    Config data as if obtained from yaml file.
    'variables' section must contains only one string, list and dict.
    :return:
    dict based data structure
    """
    def _callback(provider='pinocchio',
                  az_region='westeurope',
                  hana_ips=None,
                  hana_disk_configuration=None):

        # Default values
        hana_ips = hana_ips if hana_ips else ['10.0.0.2', '10.0.0.3']
        hana_disk_configuration = hana_disk_configuration if \
            hana_disk_configuration else {'disk_type': 'hdd,hdd,hdd', 'disks_size': '64,64,64'}

        # Config template
        config = {
            "name": "geppetto",
            "terraform": {
                "provider": provider,
                "variables": {
                    "az_region": az_region,
                    "hana_ips": hana_ips,
                    "hana_data_disks_configuration": hana_disk_configuration,
                },
            },
            "ansible": {
                "hana_urls": ["SAPCAR_URL", "SAP_HANA_URL", "SAP_CLIENT_SAR_URL"]
            },
        }

        return config
    return _callback


@pytest.fixture
def config_yaml_sample():
    """
    create yaml config data sample with one string, list and dict variable.
    :return:
    dict based data structure
    """
    config = """---
apiver: {}
provider: {}
terraform:
  variables:
    az_region: "westeurope"
    hana_ips: ["10.0.0.2", "10.0.0.3"]
    hana_data_disks_configuration:
      disk_type: "hdd,hdd,hdd"
      disks_size: "64,64,64"
ansible:
  hana_urls:
    - SAPCAR_URL
    - SAP_HANA_URL
    - SAP_CLIENT_SAR_URL
  hana_vars:
    sap_hana_install_software_directory: /hana/shared/install
    sap_hana_install_master_password: 'DoNotUseThisPassw0rd'
    sap_hana_install_sid: 'HDB'
    sap_hana_install_instance_number: '00'
    sap_domain: "qe-test.example.com"
"""

    def _callback(provider='pinocchio', apiver=2):
        return config.format(apiver, provider)

    return _callback


@pytest.fixture
def provider_dir(tmpdir):
    def _callback(provider):
        provider_path = os.path.join(tmpdir, 'terraform', provider)
        if not os.path.isdir(provider_path):
            os.makedirs(provider_path)
        return provider_path

    return _callback


@pytest.fixture
def playbooks_dir(tmpdir):
    def _callback():
        playbooks_path = os.path.join(tmpdir, 'ansible', 'playbooks')
        if not os.path.isdir(playbooks_path):
            os.makedirs(playbooks_path)
        return playbooks_path

    return _callback


@pytest.fixture
def create_playbooks(playbooks_dir):
    def _callback(playbook_list):
        playbook_filename_list = []
        for playbook in playbook_list:
            ans_plybk_path = playbooks_dir()
            playbook_filename = os.path.join(ans_plybk_path, playbook + '.yaml')
            with open(playbook_filename, 'w', encoding='utf-8') as file:
                file.write("")
            playbook_filename_list.append(playbook_filename)
        return playbook_filename_list

    return _callback


@pytest.fixture
def ansible_config():
    def _callback(provider, playbooks):
        config_content = f"""---
apiver: 2
provider: {provider}
ansible:
    hana_urls: somesome"""

        for seq in ['create', 'destroy']:
            if seq in playbooks:
                config_content += f"\n    {seq}:"""
                for play in playbooks[seq]:
                    config_content += f"\n        - {play}.yaml"
        return config_content

    return _callback


@pytest.fixture
def create_inventory(provider_dir):
    """
    Create an empty inventory file
    """
    def _callback(provider):
        provider_path = provider_dir(provider)
        inventory_filename = os.path.join(provider_path, 'inventory.yaml')
        with open(inventory_filename, 'w', encoding='utf-8') as file:
            file.write("")
        return inventory_filename

    return _callback


@pytest.fixture
def base_args(tmpdir):
    """
    Return bare minimal list of arguments to run any sub-command
    Args:
        base_dir (str): used for -b
        config_file (str): used for -c
    """
    def _callback(base_dir=None, config_file=None, verbose=True):
        args = []
        if verbose:
            args.append('--verbose')

        args.append('--base-dir')
        if base_dir is None:
            args.append(str(tmpdir))
        else:
            args.append(str(base_dir))

        args.append('--config-file')
        if config_file is None:
            # create an empty config.yaml
            config_file_name = str(tmpdir / 'config.yaml')
            with open(config_file_name, 'w', encoding='utf-8') as file:
                file.write("")
            args.append(config_file_name)
        else:
            args.append(config_file)
        return args

    return _callback


@pytest.fixture
def args_helper(tmpdir, base_args, provider_dir):
    def _callback(provider, conf, tfvar_template):
        provider_path = provider_dir(provider)
        tfvar_path = os.path.join(provider_path, 'terraform.tfvars')

        ansiblevars_path = os.path.join(tmpdir, 'ansible', 'playbooks', 'vars')
        if not os.path.isdir(ansiblevars_path):
            os.makedirs(ansiblevars_path)
        hana_media = os.path.join(ansiblevars_path, 'hana_media.yaml')
        hana_vars = os.path.join(ansiblevars_path, 'hana-vars.yaml')

        config_file_name = str(tmpdir / 'config.yaml')
        with open(config_file_name, 'w', encoding='utf-8') as file:
            file.write(conf)
        if tfvar_template is not None and len(tfvar_template) > 0:
            with open(os.path.join(provider_path, 'terraform.tfvars.template'), 'w', encoding='utf-8') as file:
                for line in tfvar_template:
                    file.write(line)

        args = base_args(base_dir=tmpdir, config_file=config_file_name)
        return args, provider_path, tfvar_path, hana_media, hana_vars

    return _callback


@pytest.fixture
def configure_helper(args_helper):
    def _callback(provider, conf, tfvar):
        args, _, tfvar_path, hana_media, hana_vars = args_helper(provider, conf, tfvar)
        args.append('configure')
        return args, tfvar_path, hana_media, hana_vars

    return _callback


@pytest.fixture
def create_config():
    """Create one element for the list in the configure.json related to trento_deploy.py -s
    """
    def _callback(typ, reg, ver):
        config = {
            'type': typ,
            'registry': reg
        }
        if ver:
            config['version'] = ver
        return config

    return _callback


@pytest.fixture
def line_match():
    """
    return True if matcher string is present at least one in the string_list
    """
    def _callback(string_list, matcher):
        return len([s for s in string_list if matcher in s]) > 0

    return _callback


@pytest.fixture
def check_duplicate():
    """
    Fixture to test trento_cluster_install.sh content
    Check for duplicated lines

    Args:
        lines (list(str)): list of string, each string is a trento_cluster_install.sh line

        Returns:
            tuple: True/False result, if False str about the error message
        """
    def _callback(lines):
        for line in lines:
            if len([s for s in lines if line.strip() in s.strip()]) != 1:
                return (False, "Line '" + line + "' appear more than one time")
            if '--set' in line:
                setting = line.split(' ')[1]
                setting_field = setting.split('=')[0]
                if len([s for s in lines if setting_field in s]) != 1:
                    return (False, "Setting '" + setting_field + "' appear more than one time")
        return (True, '')

    return _callback


@pytest.fixture
def check_manadatory_args(capsys, tmpdir):
    '''
    Given a cli to test and a subcommand string,
    check that both -c and -b are mandatory
    '''
    def _callback(cli_to_test, subcmd):
        try:
            cli_to_test([subcmd])
        except SystemExit:
            pass
        captured = capsys.readouterr()
        if 'error:' not in captured.err:
            return False

        # Try with b but without c
        try:
            cli_to_test(['-b', str(tmpdir), subcmd])
        except SystemExit:
            pass
        captured = capsys.readouterr()
        if 'error:' not in captured.err:
            return False

        # Try with c but without b
        try:
            cli_to_test(['-c', str(tmpdir), subcmd])
        except SystemExit:
            pass
        captured = capsys.readouterr()
        if 'error:' not in captured.err:
            return False
        return True

    return _callback


@pytest.fixture
def mock_call_ansibleplaybook():
    '''
    create a mock.call with some default elements
    ```
    mock.call(['ansible-playbook', '-i', inventory, playbook], env={'ANSIBLE_PIPELINING', 'True'})
    ```
    '''
    def _callback(playbook_cmd):
        return mock.call(cmd=playbook_cmd, env={'ANSIBLE_PIPELINING': 'True'})

    return _callback
