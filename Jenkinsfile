// GovGuide deploy pipeline.
//
// Runs on the same Linux host that serves the containers, so there is no SSH
// hop: Jenkins' own service account just needs to be in the `docker` group
// (see DOCKER.md / deployment notes for the one-time host setup).
//
// Required Jenkins credential:
//   govguide-backend-env  (Secret file)  — a full backend/.env with the real
//   GEMINI_API_KEY / GROQ_API_KEY / TAVILY_API_KEY. Never stored in git.

pipeline {
    agent any

    environment {
        PUBLIC_HOST   = '10.50.227.200'
        FRONTEND_PORT = '3001'
        BACKEND_PORT  = '8001'
        COMPOSE       = 'docker compose'
    }

    options {
        disableConcurrentBuilds()
        timeout(time: 20, unit: 'MINUTES')
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Inject backend secrets') {
            steps {
                withCredentials([file(credentialsId: 'govguide-backend-env', variable: 'BACKEND_ENV_FILE')]) {
                    sh 'cp "$BACKEND_ENV_FILE" backend/.env'
                }
            }
        }

        stage('Build images') {
            steps {
                sh '${COMPOSE} build'
            }
        }

        stage('Deploy') {
            steps {
                // Recreates only what changed; the bind-mounted backend/data
                // and the frontend build cache are untouched.
                sh '${COMPOSE} up -d --remove-orphans'
            }
        }

        stage('Health check') {
            steps {
                sh '''
                    set -e
                    for i in $(seq 1 20); do
                        if curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health" > /dev/null; then
                            echo "backend healthy"
                            break
                        fi
                        [ "$i" -eq 20 ] && { echo "backend failed health check"; exit 1; }
                        sleep 3
                    done
                    curl -fsS "http://127.0.0.1:${FRONTEND_PORT}/" > /dev/null
                    echo "frontend healthy"
                '''
            }
        }
    }

    post {
        always {
            sh '${COMPOSE} ps'
        }
        failure {
            sh '${COMPOSE} logs --tail=100'
        }
        cleanup {
            // Drop the plaintext secrets copy from the workspace; the running
            // container already has them in its env, this is just cleanup of
            // the checkout dir.
            sh 'rm -f backend/.env'
        }
    }
}
