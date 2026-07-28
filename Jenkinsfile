pipeline {
    agent any
    stages {
        stage('Checkout') {
            steps {
                checkout scm
                echo '웹훅 > Jenkins 파이프라인 작동 확인!'
                sh 'ls -al'
                sh 'git log -1 --oneline'
            }
        }
    }
}