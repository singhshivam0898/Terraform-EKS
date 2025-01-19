import pytest
import json
import os
import hcl2
from pathlib import Path

class TestEKSConfiguration:
    @pytest.fixture
    def terraform_config(self):
        """Fixture to load the Terraform configuration"""
        tf_file = Path("modules/aws_eks/main.tf")
        with open(tf_file, 'r') as f:
            return hcl2.load(f)

    def test_eks_cluster_configuration(self, terraform_config):
        """Test EKS cluster basic configuration"""
        eks_cluster = None
        for resource in terraform_config['resource']:
            if 'aws_eks_cluster' in resource:
                eks_cluster = resource['aws_eks_cluster']['example']
                break
        
        assert eks_cluster is not None
        assert 'version' in eks_cluster
        assert eks_cluster['version'] == "1.31"
        assert 'vpc_config' in eks_cluster
        assert 'access_config' in eks_cluster
        assert eks_cluster['access_config']['authentication_mode'] == "API"

    def test_iam_role_configuration(self, terraform_config):
        """Test IAM role configuration"""
        iam_role = None
        for resource in terraform_config['resource']:
            if 'aws_iam_role' in resource:
                iam_role = resource['aws_iam_role']['cluster']
                break

        assert iam_role is not None
        assert 'name' in iam_role
        assert iam_role['name'] == "eks-cluster-example"

        # Test assume role policy
        assume_role_policy = json.loads(iam_role['assume_role_policy'])
        assert assume_role_policy['Version'] == "2012-10-17"
        assert len(assume_role_policy['Statement']) > 0
        assert "sts:AssumeRole" in assume_role_policy['Statement'][0]['Action']
        assert assume_role_policy['Statement'][0]['Effect'] == "Allow"
        assert assume_role_policy['Statement'][0]['Principal']['Service'] == "eks.amazonaws.com"

    def test_policy_attachments(self, terraform_config):
        """Test IAM policy attachments"""
        policy_attachments = []
        for resource in terraform_config['resource']:
            if 'aws_iam_role_policy_attachment' in resource:
                policy_attachments.extend(resource['aws_iam_role_policy_attachment'].values())

        # Check if we have the required policies
        policy_arns = [p['policy_arn'] for p in policy_attachments]
        required_policies = [
            "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
            "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
        ]

        for policy in required_policies:
            assert policy in policy_arns

    def test_dependencies(self, terraform_config):
        """Test resource dependencies"""
        eks_cluster = None
        for resource in terraform_config['resource']:
            if 'aws_eks_cluster' in resource:
                eks_cluster = resource['aws_eks_cluster']['example']
                break

        assert 'depends_on' in eks_cluster
        dependencies = eks_cluster['depends_on']
        assert len(dependencies) >= 2
        
        # Check for required dependencies
        dependency_names = [str(dep) for dep in dependencies]
        assert any("cluster_AmazonEKSClusterPolicy" in dep for dep in dependency_names)
        assert any("AmazonEC2ContainerRegistryReadOnly" in dep for dep in dependency_names)

def test_file_structure():
    """Test the existence of required Terraform files"""
    module_path = Path("modules/aws_eks")
    assert module_path.exists(), "Module directory does not exist"
    assert (module_path / "main.tf").exists(), "main.tf is missing"

if __name__ == "__main__":
    pytest.main(["-v"])
