# Configuración de GitHub Actions para Terraform

## 🚀 Backend Remoto Configurado

Este proyecto ahora usa un **backend remoto de Terraform** en Google Cloud Storage para compartir el estado entre entornos locales y GitHub Actions.

### 📁 Archivos de Estado
- **Bucket:** `gs://testados-terraform-state`
- **Prefijo:** `terraform/state`
- **Archivo:** `terraform.tfstate`

## 🔑 Configuración en GitHub Actions

### 1. Variables de Entorno Requeridas

```yaml
env:
  GOOGLE_PROJECT_ID: estado-eb18c
  GOOGLE_REGION: us-central1
```

### 2. Autenticación con Google Cloud

```yaml
- name: Setup Google Cloud CLI
  uses: google-github-actions/setup-gcloud@v1
  with:
    project_id: ${{ env.GOOGLE_PROJECT_ID }}
    service_account_key: ${{ secrets.GCP_SA_KEY }}
    export_default_credentials: true
```

### 3. Inicializar Terraform

```yaml
- name: Terraform Init
  run: terraform init
  working-directory: ./TestadosInfra
```

### 4. Aplicar Cambios

```yaml
- name: Terraform Apply
  run: terraform apply -auto-approve
  working-directory: ./TestadosInfra
```

## 🔐 Secretos Requeridos en GitHub

### `GCP_SA_KEY`
- Clave de cuenta de servicio con permisos para:
  - `roles/storage.admin` (para el bucket de estado)
  - `roles/cloudfunctions.admin`
  - `roles/iam.securityAdmin`
  - `roles/pubsub.admin`
  - `roles/cloudscheduler.admin`

## 📋 Workflow Completo

```yaml
name: Deploy Infrastructure

on:
  push:
    branches: [ main ]
    paths: [ 'TestadosInfra/**' ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Google Cloud CLI
      uses: google-github-actions/setup-gcloud@v1
      with:
        project_id: ${{ env.GOOGLE_PROJECT_ID }}
        service_account_key: ${{ secrets.GCP_SA_KEY }}
        export_default_credentials: true
    
    - name: Setup Terraform
      uses: hashicorp/setup-terraform@v2
      with:
        terraform_version: 1.5.7
    
    - name: Terraform Init
      run: terraform init
      working-directory: ./TestadosInfra
    
    - name: Terraform Plan
      run: terraform plan
      working-directory: ./TestadosInfra
    
    - name: Terraform Apply
      run: terraform apply -auto-approve
      working-directory: ./TestadosInfra
```

## ✅ Ventajas del Backend Remoto

1. **Estado compartido** entre local y CI/CD
2. **Sin conflictos** de estado
3. **Automatización completa** sin intervención manual
4. **Colaboración en equipo** más fácil
5. **Historial de cambios** en el estado

## 🚨 Importante

- **Nunca committear** archivos `.tfstate` o `.terraform/`
- **Usar siempre** `terraform init` después de clonar
- **Verificar permisos** de la cuenta de servicio en GitHub Actions
