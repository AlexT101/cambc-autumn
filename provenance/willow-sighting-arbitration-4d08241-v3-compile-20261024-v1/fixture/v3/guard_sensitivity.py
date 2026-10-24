#!/usr/bin/env python3
"""Mutate only generated host-test C++ to prove two targeted assertions detect removed guards."""
import hashlib, json, pathlib, subprocess
here=pathlib.Path(__file__).resolve().parent
base=(here/'production_protocol_fixture.cpp').read_text()
mutations=[
 ('same-round-replacement-marker','witness','|| sight_replaced.get(bits)','|| false','same-round marker blocks changed same-enemy confirmation payload'),
 ('nonconsecutive-publication-guard','gap-marker0','|| !state.consecutive','|| false','nonconsecutive send does not refresh current-parity sighting or increment generation'),
]
results=[]
for name,mode,old,new,expected in mutations:
 assert base.count(old)==1,(name,'mutation anchor count',base.count(old))
 source=base.replace(old,new,1)
 src=here/'sensitivity'/f'{name}.mutant.cpp';exe=here/'sensitivity'/f'{name}.mutant';log=here/'sensitivity'/f'{name}.run.log'
 src.write_text(source)
 cmd=['clang++','-std=c++20','-O0','-Wall','-Wextra','-Werror=return-type',str(src),'-o',str(exe)]
 cp=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 if cp.returncode: raise SystemExit(f'{name}: mutant compilation failed: {cp.stdout}')
 run=subprocess.run([str(exe),mode],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 log.write_text(run.stdout)
 if run.returncode==0 or expected not in run.stdout:
  raise SystemExit(f'{name}: assertion was not sensitive; rc={run.returncode}, output={run.stdout!r}')
 results.append({'guard':name,'mutation':{'replace_once':old,'with':new},'targeted_scenario':mode,'expected_failing_assertion':expected,'mutant_cpp_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'mutant_binary_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'run_log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'exit_code':run.returncode,'assertion_failed_as_expected':True})
receipt={'schema':'sighting-protocol-fixture-guard-sensitivity/v1','original_generated_cpp_sha256':hashlib.sha256((here/'production_protocol_fixture.cpp').read_bytes()).hexdigest(),'tests':results,'note':'Both mutations apply only to generated host-fixture C++; production source and production fixture runner are unchanged.'}
(here/'sensitivity'/'RESULT.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('PASS: both targeted assertions fail under removal of their corresponding production guard')
print(json.dumps(results,indent=2))
