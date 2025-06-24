# Отчет об ошибках тестирования - 24.06.2025

В процессе тестирования интерфейса Streamlit была выявлена следующая ошибка:

**Ошибка:**
```
2025-06-24 22:18:08.809 Serialization of dataframe to Arrow table was unsuccessful. Applying automatic fixes for column types to make the dataframe Arrow-compatible.
Traceback (most recent call last):
  File "f:\PythonProjects\binance_correlation_script\.venv\Lib\site-packages\streamlit\dataframe_util.py", line 822, in convert_pandas_df_to_arrow_bytes
    table = pa.Table.from_pandas(df)
  File "pyarrow\\table.pxi", line 4793, in pyarrow.lib.Table.from_pandas
  File "f:\PythonProjects\binance_correlation_script\.venv\Lib\site-packages\pyarrow\pandas_compat.py", line 639, in dataframe_to_arrays
    arrays = [convert_column(c, f)
              ~~~~~~~~~~~~~~^^^^^^
  File "f:\PythonProjects\binance_correlation_script\.venv\Lib\site-packages\pyarrow\pandas_compat.py", line 626, in convert_column
    raise e
  File "f:\PythonProjects\binance_correlation_script\.venv\Lib\site-packages\pyarrow\pandas_compat.py", line 620, in convert_column
    result = pa.array(col, type=type_, from_pandas=True, safe=safe)
  File "pyarrow\\array.pxi", line 365, in pyarrow.lib.array
  File "pyarrow\\array.pxi", line 90, in pyarrow.lib._ndarray_to_array
  File "pyarrow\\error.pxi", line 92, in pyarrow.lib.check_status
pyarrow.lib.ArrowTypeError: ("Expected bytes, got a 'int' object", "Conversion failed for column Значение with type object")
```

**Причина:**
Ошибка `ArrowTypeError` возникает, когда столбец в DataFrame, передаваемый в `st.dataframe()`, содержит смешанные типы данных. В данном случае, столбец 'Значение' содержал как строки (например, `"$1050.25"`), так и целые числа (например, `25`). Библиотека Arrow, используемая Streamlit для отображения таблиц, не может обработать такой столбец.

**Решение:**
Привести все значения в столбце 'Значение' к строковому типу (`str`) перед созданием DataFrame и его отображением.
