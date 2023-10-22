from kubernetes import client, config
import os
import yaml
import subprocess

# Load kubeconfig
config.load_kube_config()

# Initialize the API client
v1 = client.CoreV1Api()

# Fetch the list of namespaces
namespace_list = v1.list_namespace()

def clean_kubernetes_object(k8s_dict):
    # Remove metadata.creationTimestamp, metadata.selfLink, metadata.uid, metadata.resourceVersion, etc.
    k8s_dict['metadata'] = {k: v for k, v in k8s_dict['metadata'].items() if k not in ['creationTimestamp', 'selfLink', 'uid', 'resourceVersion', 'generation', 'managedFields']}
    # Remove spec.clusterIP for services, spec.volumeName for persistent volumes, etc.
    if 'spec' in k8s_dict:
        k8s_dict['spec'] = {k: v for k, v in k8s_dict['spec'].items() if k not in ['clusterIP', 'volumeName']}
    # Remove status field
    if 'status' in k8s_dict:
        del k8s_dict['status']
    return k8s_dict


# Load kubeconfig
config.load_kube_config()

# Initialize the API client
v1 = client.CoreV1Api()

# Fetch the list of namespaces
namespace_list = v1.list_namespace()

# Prepare the test suite dictionary
test_suite = {
    'apiVersion': 'kuttl.dev/v1beta1',
    'kind': 'TestSuite',
    'testDirs': [],
}

# Loop through all namespaces
for namespace in namespace_list.items:
    ns_name = namespace.metadata.name

    # Fetch the names of all deployments in the namespace
    result = subprocess.run(['kubectl', 'get', 'deployments', '-n', ns_name, '-o', 'name'], stdout=subprocess.PIPE)
    deployments = result.stdout.decode('utf-8').strip().split('\n')

    if not deployments or deployments[0] == '':
        continue

    for deployment_name in deployments:
        deployment_name = deployment_name.split('/')[1]

        # Fetch the deployment YAML
        result = subprocess.run(['kubectl', 'get', 'deployment', deployment_name, '-n', ns_name, '-o', 'yaml'], stdout=subprocess.PIPE)
        raw_yaml = result.stdout.decode('utf-8')

        # Clean the yaml
        loaded_yaml = yaml.safe_load(raw_yaml)
        cleaned_yaml_dict = clean_kubernetes_object(loaded_yaml)
        cleaned_yaml = yaml.safe_dump(cleaned_yaml_dict)

        kuttl_test_dir = f'my-kuttl-tests/{ns_name}/{deployment_name}'
        os.makedirs(kuttl_test_dir, exist_ok=True)

        file_path = f'{kuttl_test_dir}/01-assert.yaml'
        with open(file_path, 'w') as f:
            f.write(cleaned_yaml)

        print(f"Wrote cleaned assert file to {os.path.abspath(file_path)}")

        # Add this directory to the test suite
        test_suite['testDirs'].append(f'my-kuttl-tests/{ns_name}/{deployment_name}')

# Write the test suite configuration to kuttl-test.yaml
with open('my-kuttl-tests/kuttl-test.yaml', 'w') as f:
    yaml.safe_dump(test_suite, f)

print("The cleaned assert.yaml files have been created and the test suite has been configured.")