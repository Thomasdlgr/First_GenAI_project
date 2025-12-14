# Script pour configurer Python 3.12 comme alias 'python' dans PowerShell
# Exécutez ce script dans votre session PowerShell avec: . .\setup_python.ps1

# Créer un alias pour python vers py -3.12
Set-Alias -Name python -Value "py" -Scope Global -Force

# Fonction pour utiliser python avec Python 3.12
function python {
    param([Parameter(ValueFromRemainingArguments=$true)]$args)
    & py -3.12 $args
}

# Vérifier la version
Write-Host "Python configuré pour utiliser Python 3.12" -ForegroundColor Green
python --version

