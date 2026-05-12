import os
import subprocess

def run_pipeline():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    vev_python = os.path.join(base_dir, '.venv', 'bin', 'python3')
    src_dir = os.path.join(base_dir, 'src')

    scripts = [
        ("Sincronizando Google Drive", "drive_sync.py"),
        ("Extraindo PDFs e Estruturando", "extractor.py"),
        ("Registro: Gerando Metadados", "tagger.py"),
        ("Dividindo Documentos (Chunking)", "chunker.py"),
        ("Vetorizando Coordenadas (Embeddings)", "embedder.py")
    ]
    print("\n" + "="*50)
    print("INICIANDO INGESTÃO (SNOOPY WATCHER)")
    print("="*50)


    for step_name, script_name in scripts:
        script_path = os.path.join(src_dir, script_name)
        print(f"\nPasso: {step_name} ({script_name})...")

        try:
            result = subprocess.run(
                [vev_python, script_path],
                check=True,
            )
            print("Concluído")

            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"\nERRO FATAL no módulo: {script_name}!")
            print(f"Detalhes:\n{e.stderr}")
            return False
    
    print("\n" + "="*50)
    print("INGESTÃO CONCLUÍDA")
    print("Banco de dados atualizado.")
    print("="*50)
    return True

if __name__ == '__main__':
    run_pipeline()