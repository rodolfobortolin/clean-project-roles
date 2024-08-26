import os
import requests
import logging
import csv
from requests.auth import HTTPBasicAuth
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configurações de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')

# Configurações de autenticação e URL base da API
config = {
    'email': 'rodolfo.bortolin@valiantys.com',  
    'token': '',  
    'base_url': 'https://domain.atlassian.net',
}

# Caminho dos arquivos CSV de saída
OUTPUT_CSV = 'workflow_transition_rules.csv'
SPECIAL_CSV = 'special_conditions_functions.csv'
PAGE_SIZE = 50  # Número de itens por página
MAX_WORKERS = 10  # Número máximo de threads simultâneas

# Função para buscar uma página de workflows
def fetch_workflows_page(start_at):
    url = f"{config['base_url']}/rest/api/2/workflow/search"
    auth = HTTPBasicAuth(config['email'], config['token'])
    params = {
        "expand": "transitions.rules",
        "startAt": start_at,
        "maxResults": PAGE_SIZE
    }
    response = requests.get(url, auth=auth, params=params, headers={"Accept": "application/json"})

    if response.status_code != 200:
        logging.error(f"Erro ao buscar workflows na página {start_at}: {response.status_code} - {response.text}")
        return []

    data = response.json()
    return data.get('values', []), data.get('isLast', True)

# Função para buscar todos os workflows utilizando multithreading
def get_all_workflows():
    all_workflows = []
    start_at = 0
    is_last = False

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        while not is_last:
            futures = [executor.submit(fetch_workflows_page, start_at)]
            for future in as_completed(futures):
                workflows, is_last = future.result()
                all_workflows.extend(workflows)
                start_at += PAGE_SIZE

    return all_workflows

# Função para processar os workflows e armazenar as regras das transições nos CSVs
def process_workflows_and_save_details():
    workflows = get_all_workflows()
    
    logging.info(f"Total de workflows encontrados: {len(workflows)}")

    with open(OUTPUT_CSV, mode='w', newline='') as output_file, \
         open(SPECIAL_CSV, mode='w', newline='') as special_file:
        
        writer = csv.writer(output_file)
        special_writer = csv.writer(special_file)
        
        writer.writerow([
            'Workflow Name', 'Workflow ID', 'Transition ID', 'Transition Name', 
            'Condition Type', 'Condition Configuration', 'Validator Type', 
            'Validator Configuration', 'Post Function Type', 
            'Post Function Configuration'
        ])
        
        special_writer.writerow([
            'Workflow Name', 'Workflow ID', 'Transition ID', 'Transition Name', 
            'Condition Type', 'Condition Configuration', 'Validator Type', 
            'Validator Configuration', 'Post Function Type', 
            'Post Function Configuration'
        ])

        excluded_functions = {
            'IssueReindexFunction', 
            'GenerateChangeHistoryFunction', 
            'CreateCommentFunction', 
            'UpdateIssueStatusFunction', 
            'FireIssueEventFunction',
            'IssueCreateFunction'
        }

        special_conditions = {'InProjectRoleCondition'}
        special_functions = {'SetIssueSecurityFromRoleFunction'}

        for workflow in workflows:
            workflow_name = workflow.get('id', {}).get('name', 'Unknown')
            workflow_id = workflow.get('id', {}).get('entityId', 'Unknown')

            # Processar transições
            for transition in workflow.get('transitions', []):
                transition_id = transition.get('id', 'Unknown')
                transition_name = transition.get('name', 'Unknown')

                # Extrair regras: conditions, validators e post functions
                conditions = transition.get('rules', {}).get('conditionsTree', {})
                validators = transition.get('rules', {}).get('validators', [])
                post_functions = transition.get('rules', {}).get('postFunctions', [])

                should_write_to_special = False

                # Processar conditions
                if conditions:
                    if conditions.get('nodeType') == 'simple':
                        condition_type = conditions.get('type', 'Unknown')
                        condition_config = conditions.get('configuration', {})
                    else:
                        condition_type = "Complex"
                        condition_config = conditions
                        #logging.info(f"Complex condition found in workflow '{workflow_name}', transition '{transition_name}': {conditions}")

                    if condition_type in special_conditions:
                        should_write_to_special = True

                    for validator in validators:
                        validator_type = validator.get('type', 'Unknown')
                        if validator_type == 'PermissionValidator' and transition_id == '1':
                            continue
                        validator_config = validator.get('configuration', {})

                        for post_function in post_functions:
                            post_function_type = post_function.get('type', 'Unknown')
                            if post_function_type in excluded_functions:
                                continue
                            if post_function_type in special_functions:
                                should_write_to_special = True
                            post_function_config = post_function.get('configuration', {})

                            writer.writerow([
                                workflow_name, workflow_id, transition_id, transition_name, 
                                condition_type, str(condition_config), validator_type, 
                                str(validator_config), post_function_type, 
                                str(post_function_config)
                            ])

                            if should_write_to_special:
                                special_writer.writerow([
                                    workflow_name, workflow_id, transition_id, transition_name, 
                                    condition_type, str(condition_config), validator_type, 
                                    str(validator_config), post_function_type, 
                                    str(post_function_config)
                                ])
                    # If no validators, still need to capture post functions
                    if not validators:
                        for post_function in post_functions:
                            post_function_type = post_function.get('type', 'Unknown')
                            if post_function_type in excluded_functions:
                                continue
                            if post_function_type in special_functions:
                                should_write_to_special = True
                            post_function_config = post_function.get('configuration', {})

                            writer.writerow([
                                workflow_name, workflow_id, transition_id, transition_name, 
                                condition_type, str(condition_config), '', '', 
                                post_function_type, str(post_function_config)
                            ])

                            if should_write_to_special:
                                special_writer.writerow([
                                    workflow_name, workflow_id, transition_id, transition_name, 
                                    condition_type, str(condition_config), '', '', 
                                    post_function_type, str(post_function_config)
                                ])
                else:
                    for validator in validators:
                        validator_type = validator.get('type', 'Unknown')
                        if validator_type == 'PermissionValidator' and transition_id == '1':
                            continue
                        validator_config = validator.get('configuration', {})

                        for post_function in post_functions:
                            post_function_type = post_function.get('type', 'Unknown')
                            if post_function_type in excluded_functions:
                                continue
                            if post_function_type in special_functions:
                                should_write_to_special = True
                            post_function_config = post_function.get('configuration', {})

                            writer.writerow([
                                workflow_name, workflow_id, transition_id, transition_name, 
                                '', '', validator_type, str(validator_config), 
                                post_function_type, str(post_function_config)
                            ])

                            if should_write_to_special:
                                special_writer.writerow([
                                    workflow_name, workflow_id, transition_id, transition_name, 
                                    '', '', validator_type, str(validator_config), 
                                    post_function_type, str(post_function_config)
                                ])
                    # If no validators, still need to capture post functions
                    if not validators:
                        for post_function in post_functions:
                            post_function_type = post_function.get('type', 'Unknown')
                            if post_function_type in excluded_functions:
                                continue
                            if post_function_type in special_functions:
                                should_write_to_special = True
                            post_function_config = post_function.get('configuration', {})

                            writer.writerow([
                                workflow_name, workflow_id, transition_id, transition_name, 
                                '', '', '', '', post_function_type, str(post_function_config)
                            ])

                            if should_write_to_special:
                                special_writer.writerow([
                                    workflow_name, workflow_id, transition_id, transition_name, 
                                    '', '', '', '', post_function_type, str(post_function_config)
                                ])

# Execução do script
if __name__ == "__main__":
    try:
        process_workflows_and_save_details()
        logging.info(f"Regras das transições foram armazenadas em {OUTPUT_CSV} e {SPECIAL_CSV}")
    except Exception as e:
        logging.error(f"Ocorreu um erro: {str(e)}")
