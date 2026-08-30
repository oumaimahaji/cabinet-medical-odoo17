pipeline {
    agent any

    environment {
        NEXUS_REGISTRY = '192.168.33.10:8083'
        NEXUS_CREDENTIALS_ID = 'nexus-docker-credentials'
        IMAGE_NAME = 'cabinet-medical-odoo'
        IMAGE_TAG = "17.0.${BUILD_NUMBER}"
        SONAR_SCANNER_HOME = tool 'SonarScanner'
    }

    stages {
        // =================================================================
        // STAGE 1 : RÉCUPÉRATION DU CODE DEPUIS GIT
        // =================================================================
        stage('Checkout SCM') {
            steps {
                echo '📦 Récupération du code source depuis Git...'
                checkout scm
            }
        }

        // =================================================================
        // STAGE 2 : ENVIRONNEMENT PYTHON
        // =================================================================
        stage('Install Dependencies') {
            steps {
                echo '🐍 Préparation de l environnement Python...'
                sh '''
                    if [ ! -d "/var/jenkins_home/shared_venv" ]; then
                        python3 -m venv /var/jenkins_home/shared_venv
                    fi
                    . /var/jenkins_home/shared_venv/bin/activate
                    pip install --no-cache-dir scikit-learn joblib pandas numpy passlib openpyxl torch sentence-transformers --extra-index-url https://download.pytorch.org/whl/cpu
                    echo "✅ Environnement virtuel prêt !"
                '''
            }
        }

        // =================================================================
        // STAGE 3 : TESTS UNITAIRES MÉDICAUX & IA
        // =================================================================
        stage('Unit Tests') {
            steps {
                echo '🧪 Exécution de la suite complète des 102 tests unitaires...'
                sh '''
                    . /var/jenkins_home/shared_venv/bin/activate
                    python3 -u custom_addons/cabinet_medical/tests/run_unit_tests.py
                '''
            }
        }

        // =================================================================
        // STAGE 4 : ANALYSE STATIQUE DU CODE (SONARQUBE)
        // =================================================================
        stage('SonarQube Analysis') {
            steps {
                echo '🔍 Lancement de l analyse de qualité SonarQube...'
                script {
                    withSonarQubeEnv('SonarQube') {
                        withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
                            sh '$SONAR_SCANNER_HOME/bin/sonar-scanner -Dsonar.token=$SONAR_TOKEN'
                        }
                    }
                }
            }
        }

        // =================================================================
        // STAGE 5 : QUALITY GATE (VALIDATION DE QUALITÉ)
        // =================================================================
        stage('Quality Gate') {
            steps {
                echo '🚦 Validation du Quality Gate SonarQube...'
                timeout(time: 10, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        // =================================================================
        // STAGE 6 : CONSTRUCTION DE L IMAGE DOCKER
        // =================================================================
        stage('Docker Build') {
            steps {
                echo "🐳 Construction de l'image Docker personnalisée Odoo 17..."
                sh """
                    docker build -t ${IMAGE_NAME}:${IMAGE_TAG} -t ${IMAGE_NAME}:latest -f docker-deploy/Dockerfile .
                    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${NEXUS_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
                    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${NEXUS_REGISTRY}/${IMAGE_NAME}:latest
                """
            }
        }

        // =================================================================
        // STAGE 7 : PUBLICATION VERS NEXUS (REGISTRY PRIVÉ)
        // =================================================================
        stage('Push to Nexus') {
            steps {
                echo '📤 Publication de l\'image Docker vers Nexus (192.168.33.10:8083)...'
                withCredentials([usernamePassword(credentialsId: 'nexus-docker-credentials', usernameVariable: 'NEXUS_USER', passwordVariable: 'NEXUS_PWD')]) {
                    sh '''
                        echo "$NEXUS_PWD" | docker login "$NEXUS_REGISTRY" -u "$NEXUS_USER" --password-stdin
                        docker push "$NEXUS_REGISTRY/${IMAGE_NAME}:latest"
                        docker push "$NEXUS_REGISTRY/${IMAGE_NAME}:${IMAGE_TAG}"
                    '''
                }
            }
        }

        // =================================================================
        // STAGE 8 : DÉPLOIEMENT CONTINU (DOCKER)
        // =================================================================
        stage('Deploy Application') {
            steps {
                echo '🚀 Déploiement propre du conteneur Odoo 17 & PostgreSQL...'
                sh '''
                    docker stop cabinet_odoo cabinet-deploy-odoo-1 2>/dev/null || true
                    docker rm cabinet_odoo cabinet-deploy-odoo-1 2>/dev/null || true
                    cd docker-deploy
                    if docker compose version >/dev/null 2>&1; then
                        docker compose up -d --force-recreate
                    else
                        docker-compose up -d --force-recreate
                    fi
                '''
            }
        }

        // =================================================================
        // STAGE 9 : SMOKE TEST (VÉRIFICATION DE SANTÉ HTTP)
        // =================================================================
        stage('Health Check') {
            steps {
                echo '🏥 Vérification de la disponibilité du serveur Odoo sur le port 8069...'
                sh '''
                    MAX_RETRIES=15
                    DELAY=4
                    URL_EXTERNAL="http://192.168.33.10:8069"
                    URL_LOCAL="http://localhost:8069"
                    SUCCESS=0

                    echo "Attente de la disponibilité d'Odoo 17..."
                    for i in $(seq 1 $MAX_RETRIES); do
                        echo "Tentative $i/$MAX_RETRIES..."
                        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$URL_EXTERNAL" || curl -s -o /dev/null -w "%{http_code}" "$URL_LOCAL" || echo "000")
                        echo "Code HTTP reçu: $HTTP_CODE"

                        if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "303" ] || [ "$HTTP_CODE" = "302" ]; then
                            echo "✅ Odoo 17 opérationnel et accessible (HTTP $HTTP_CODE) !"
                            SUCCESS=1
                            break
                        fi
                        sleep $DELAY
                    done

                    if [ $SUCCESS -ne 1 ]; then
                        echo "❌ Échec du Health Check : Le serveur Odoo 17 n'a pas répondu à temps sur le port 8069."
                        exit 1
                    fi
                '''
            }
        }
    }

    post {
        always {
            echo '🧹 Nettoyage des artefacts temporaires...'
            cleanWs()
        }
        success {
            echo '✅ Pipeline CI/CD terminé avec succès ! Application déployée et fonctionnelle.'
        }
        failure {
            echo '❌ Échec du Pipeline CI/CD. Veuillez inspecter les logs du stage défaillant.'
        }
    }
}
