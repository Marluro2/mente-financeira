# Cria, nesta pasta, os atalhos "Mente Financeira" e "Mente Financeira (Administrador)".
# Os atalhos abrem o jogo direto em janela propria, sem terminal, com o icone do jogo.
# Chamado pelo CRIAR_ATALHOS.bat (e pelo INSTALAR.bat). Se a pasta do jogo for
# movida, basta executar o CRIAR_ATALHOS.bat de novo.

$ErrorActionPreference = "Stop"
$pasta = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonw = Join-Path $pasta ".venv\Scripts\pythonw.exe"
$iniciador = Join-Path $pasta "iniciar_janela_app.py"
$icone = Join-Path $pasta "assets\icone.ico"

if (-not (Test-Path $pythonw)) {
    Write-Host "O jogo ainda nao foi instalado. Execute INSTALAR.bat primeiro."
    exit 1
}

$shell = New-Object -ComObject WScript.Shell
$atalhos = @(
    @{ Nome = "Mente Financeira.lnk"; Args = "`"$iniciador`""; Descricao = "Jogar Mente Financeira" },
    @{ Nome = "Mente Financeira (Administrador).lnk"; Args = "`"$iniciador`" --admin"; Descricao = "Mente Financeira - modo administrador (professor)" }
)
foreach ($a in $atalhos) {
    $lnk = $shell.CreateShortcut((Join-Path $pasta $a.Nome))
    $lnk.TargetPath = $pythonw
    $lnk.Arguments = $a.Args
    $lnk.WorkingDirectory = $pasta
    $lnk.Description = $a.Descricao
    if (Test-Path $icone) { $lnk.IconLocation = "$icone,0" }
    $lnk.Save()
    Write-Host "Atalho criado: $($a.Nome)"
}
