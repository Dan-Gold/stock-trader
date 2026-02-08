clear
clear

ruff check ./ --fix

clear
clear

ruff format ./
ruff check ./ --fix

make stock-trader-mypy
