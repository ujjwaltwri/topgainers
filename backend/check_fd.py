import financedatabase as fd

equities = fd.Equities()
df_eq = equities.select(country="South Korea")
print("Index samples:")
print(list(df_eq.index)[:10])

# check for 352770.KS
print("352770.KS in index?", "352770.KS" in df_eq.index)
print("352770 in index?", "352770" in df_eq.index)
