#!groovy
@Library('lts-basic-pipeline@epadd-curator-app-mod') _

// projName: The directory name for the project on the servers for it's docker/config files
// intTestPort: port of integration test container
// intTestEndpoints: List of integration test endpoints i.e. ['healthcheck/', 'another/example/']
// default values: slackChannel = "lts-jenkins-notifications"

def endpoints = ["curatorApp/testbatch/ePADD-eml-export", "curatorApp/testbatch/ePADD-mbox-export"]
def excludeIntTestDev = ["curatorApp/testbatch/ePADD-eml-export", "curatorApp/testbatch/ePADD-mbox-export"]
def excludeIntTestQA = []
ltsBasicPipeline.call("epadd-curator-app", "DAIS", "hdc3a", "10582", endpoints, excludeIntTestDev, excludeIntTestQA, "lts-epadd")