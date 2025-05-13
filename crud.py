import streamlit as st
import psycopg2
import yaml
from psycopg2 import errors

# Função para carregar as credenciais do arquivo YAML
def load_config():
    with open("config.yml", "r") as file:
        return yaml.safe_load(file)

# Função para conectar ao banco de dados RDS
def get_connection():
    config = load_config()
    db = config["database"]
    return psycopg2.connect(
        host=db["host"],
        port=db["port"],
        user=db["user"],
        password=db["password"],
        dbname=db["dbname"]
    )

# Funções para interagir com o banco de dados
def create_category(name, description):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categories (category_name, description) VALUES (%s, %s)", (name, description))
        conn.commit()
        conn.close()
        return True, "Categoria adicionada com sucesso!"
    except Exception as e:
        return False, f"Ops! Algo deu errado: {str(e)}"

def read_categories():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT category_id, category_name, description FROM categories")
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        st.error(f"Não foi possível carregar as categorias: {str(e)}")
        return []

def update_category(category_id, name, description):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE categories SET category_name = %s, description = %s WHERE category_id = %s", 
                      (name, description, category_id))
        conn.commit()
        conn.close()
        return True, "Categoria atualizada com sucesso!"
    except Exception as e:
        return False, f"Não foi possível atualizar: {str(e)}"

def check_category_in_use(category_id):
    """Verifica se a categoria está sendo usada por algum produto"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM products WHERE category_id = %s", (category_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return True  # Por segurança, assume que está em uso

def delete_category(category_id):
    try:
        # Primeiro verifica se a categoria está sendo usada
        if check_category_in_use(category_id):
            return False, "Esta categoria não pode ser excluída porque está sendo usada por produtos. Remova os produtos associados primeiro."
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM categories WHERE category_id = %s", (category_id,))
        conn.commit()
        conn.close()
        return True, "Categoria excluída com sucesso!"
    except errors.ForeignKeyViolation:
        return False, "Esta categoria está sendo usada por produtos e não pode ser excluída."
    except Exception as e:
        return False, f"Não foi possível excluir: {str(e)}"

# Interface do Streamlit
def main():
    st.title("Gerenciamento de Categorias")
    st.markdown("### Bem-vindo ao sistema de gerenciamento de categorias!")

    # Menu de navegação
    menu = {
        "Criar": "Criar Nova Categoria",
        "Ler": "Visualizar Categorias",
        "Atualizar": "Atualizar Categoria",
        "Deletar": "Remover Categoria"
    }
    choice = st.sidebar.radio("O que você deseja fazer?", list(menu.keys()), format_func=lambda x: menu[x])

    # Criar categoria
    if choice == "Criar":
        st.subheader("Adicionar Nova Categoria")
        st.markdown("Preencha os campos abaixo para criar uma nova categoria de produtos.")
        
        with st.form("create_form"):
            name = st.text_input("Nome da Categoria")
            description = st.text_area("Descrição")
            submitted = st.form_submit_button("Adicionar Categoria")
            
            if submitted:
                if name:
                    success, message = create_category(name, description)
                    if success:
                        st.success(message)
                        st.balloons()
                    else:
                        st.error(message)
                else:
                    st.warning("Por favor, informe um nome para a categoria.")

    # Ler categorias
    elif choice == "Ler":
        st.subheader("Categorias Disponíveis")
        categories = read_categories()
        
        if categories:
            # Criar uma tabela para melhor visualização
            data = []
            for category in categories:
                data.append({
                    "ID": category[0],
                    "Nome": category[1],
                    "Descrição": category[2] or "Sem descrição"
                })
            st.table(data)
            st.info(f"Total de categorias: {len(categories)}")
        else:
            st.info("Nenhuma categoria encontrada. Que tal criar uma?")

    # Atualizar categoria
    elif choice == "Atualizar":
        st.subheader("Atualizar Categoria")
        categories = read_categories()
        
        if categories:
            st.markdown("Selecione a categoria que deseja modificar:")
            
            # Criando uma lista mais amigável para seleção
            category_options = [f"{cat[1]} (ID: {cat[0]})" for cat in categories]
            selected_index = st.selectbox("Categoria", range(len(category_options)), format_func=lambda x: category_options[x])
            selected_category = categories[selected_index]
            
            with st.form("update_form"):
                st.markdown(f"**Editando: {selected_category[1]}**")
                new_name = st.text_input("Nome", value=selected_category[1])
                new_description = st.text_area("Descrição", value=selected_category[2] or "")
                submitted = st.form_submit_button("Salvar Alterações")
                
                if submitted:
                    if new_name:
                        success, message = update_category(selected_category[0], new_name, new_description)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                    else:
                        st.warning("O nome da categoria não pode ficar em branco.")
        else:
            st.warning("Não há categorias disponíveis para atualizar.")
            if st.button("Criar Nova Categoria"):
                st.session_state.page = "Criar"
                st.experimental_rerun()

    # Deletar categoria
    elif choice == "Deletar":
        st.subheader("Remover Categoria")
        categories = read_categories()
        
        if categories:
            st.markdown("Selecione a categoria que deseja remover:")
            
            # Criando uma lista mais amigável para seleção
            category_options = [f"{cat[1]} (ID: {cat[0]})" for cat in categories]
            selected_index = st.selectbox("Categoria", range(len(category_options)), format_func=lambda x: category_options[x])
            selected_category = categories[selected_index]
            selected_id = selected_category[0]
            
            # Verificar se a categoria está em uso
            in_use = check_category_in_use(selected_id)
            
            if in_use:
                st.warning(f"A categoria '{selected_category[1]}' está sendo usada por produtos e não pode ser excluída.")
                st.info("Dica: Você precisa primeiro remover ou reclassificar os produtos associados a esta categoria.")
            
            col1, col2 = st.columns([1, 3])
            with col1:
                delete_button = st.button("Excluir", disabled=in_use)
            
            with col2:
                if not in_use:
                    st.markdown("**Atenção**: Esta ação não pode ser desfeita!")
            
            if delete_button:
                success, message = delete_category(selected_id)
                if success:
                    st.success(message)
                else:
                    st.error(message)
        else:
            st.info("Não há categorias disponíveis para excluir.")

if __name__ == "__main__":
    main()