import os
import shutil

def limpar_banco():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, 'data', 'chroma_db')

    if os.path.exists(db_path):
        shutil.rmtree(db_path)
        print("Banco vetorial limpo!")
    else:
        print("O banco já está limpo, nada a fazer.")

if __name__ == '__main__':
    limpar_banco()