import argparse
import yaml
import re


class Translator:
    def __init__(self, input_file, output_file):
        self.input_file = input_file
        self.output_file = output_file
        self.constants = {}

    def parse_yaml(self):
        try:
            with open(self.input_file, 'r') as file:
                data = yaml.safe_load(file)
            return data
        except yaml.YAMLError as e:
            raise ValueError(f"Ошибка при разборе YAML: {e}")

    def translate_value(self, value):
        if isinstance(value, int):
            return str(value)
        elif isinstance(value, list):
            return f"<< {', '.join(map(self.translate_value, value))} >>"
        elif isinstance(value, dict):
            return self.translate_constants(value)
        else:
            raise ValueError(f"Неизвестное значение: {value}")

    def translate_constants(self, data):
        translated_lines = []
        for key, value in data.items():
            if re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', key):
                if isinstance(value, str) and value.startswith('@('):
                    evaluated_value = self.evaluate_expression(value)
                    translated_lines.append(f"{key} is {evaluated_value}")
                    self.constants[key] = evaluated_value
                elif isinstance(value, dict):
                    translated_lines.append(f"{key} is")
                    translated_lines.extend(self.translate_constants(value))
                else:
                    translated_value = self.translate_value(value)
                    translated_lines.append(f"{key} is {translated_value}")
                    self.constants[key] = value
            else:
                raise ValueError(f"Некорректное имя переменной: {key}")
        return translated_lines

    def evaluate_expression(self, expression):
        # Убираем обертки вокруг выражения
        match = re.match(r'^@\((.+)\)$', expression)
        if not match:
            raise ValueError(f"Некорректное выражение: {expression}")

        expression_body = match.group(1).strip()
        tokens = self._split_expression(expression_body)

        if len(tokens) < 2:
            raise ValueError("Операция должна содержать хотя бы два элемента.")

        op = tokens[0]
        args = []

        for token in tokens[1:]:
            if token in self.constants:
                args.append(self.constants[token])
            elif token.isdigit():
                args.append(int(token))
            elif token.startswith('(') and token.endswith(')'):
                # Обработка вложенных выражений
                args.append(self.evaluate_expression(f"@({token[1:-1]})"))
            else:
                raise ValueError(f"Неизвестная переменная или значение: {token}")

        # Обработка операций
        if op == '+':
            return sum(args)
        elif op == '-':
            if len(args) != 2:
                raise ValueError("Операция '-' ожидает два аргумента.")
            return args[0] - args[1]
        elif op == '*':
            result = 1
            for arg in args:
                result *= arg
            return result
        elif op == 'len':
            if len(args) != 1 or not isinstance(args[0], list):
                raise ValueError("Операция len() ожидает массив.")
            return len(args[0])
        elif op == 'mod':
            if len(args) != 2:
                raise ValueError("Операция mod() ожидает два аргумента.")
            return args[0] % args[1]
        else:
            raise ValueError(f"Неизвестная операция: {op}")

    def _split_expression(self, expression_body):
        """Разделяет строку выражения на токены с учётом вложенных скобок"""
        tokens = []
        temp = ''
        in_parens = 0

        for char in expression_body:
            if char == '(':
                if in_parens > 0:
                    temp += char
                in_parens += 1
            elif char == ')':
                in_parens -= 1
                if in_parens > 0:
                    temp += char
                elif in_parens == 0:
                    tokens.append(temp)
                    temp = ''
            elif char == ' ' and in_parens == 0:
                if temp:
                    tokens.append(temp)
                    temp = ''
            else:
                temp += char

        if temp:
            tokens.append(temp)

        return tokens

    def translate(self):
        data = self.parse_yaml()
        translated_lines = self.translate_constants(data)

        with open(self.output_file, 'w') as file:
            file.write('\n'.join(translated_lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Программа для перевода YAML в конфигурационный язык.")
    parser.add_argument("--input", required=True, help="Путь к входному YAML файлу.")
    parser.add_argument("--output", required=True, help="Путь к выходному файлу конфигурации.")
    args = parser.parse_args()

    try:
        translator = Translator(args.input, args.output)
        translator.translate()
        print(f"Перевод успешно завершен. Результат сохранен в {args.output}.")
    except Exception as e:
        print(f"Ошибка: {e}")