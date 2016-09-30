# APPROD
APPROD: An App to Prod Values in Deterministic Models

The software takes any deterministic simulation code (non-specific) and modifies identified variables in the input-deck for the simulation code before launching a "run" of the code. This process is repeated N times and is useful for Probabilistic Risk Assessment studies as well as any other study requiring many parametric changes to variables in a deterministic code.

This program (the Server) will launch simulation permutations based on a defined APPROD input file. The Server program was designed with the goal of being code-agnostic, and as such can be developed further to link with other simulation codes. This is accomplished through running a generic batch or shell file (depending on the platform), where the batch or shell file will specify how to launch the simulation code and any post-processing that should be performed.

After each successful individual run, APPROD can copy the results of the run and any post-processed work to a central location. In this sense it also acts as a "job-manager" which can distribute the jobs across many machines. This is useful for non-parallelized code where single-thread speed is important, such that you could group several desktops together into one distributed system.

<h2>Input file for APPROD</h2>
The "input file" to APPROD is of the form of a text file in the following format, for new runs (as opposed to branching runs). 

	Task Name,Run#,AT,PVe,.PVth,GVe,.GVth,HRTe,.HRTth,DSr,SLe,.IPL,.DHC
	Scenario,501,247.87,0.856083,0.80083,0.73539,0.993,0.83384,1.0082,1.14E-05,0.77707,0.9959,1.0232

The first row is the "header".
`Task Name` and `Run#`, spelled exactly like that, are mandatory. The combination of these values (with a space) will be the folder your results are placed in.
After `Task Name` and `Run#`, the following comma-separated values are "variable names" within your input deck (within APPROD, the input deck for your code is called the "template file". This could be confusing with an "input file" which is of the above form.)

<h2>Template file for a Simulation Code</h2>
The variables in the header should correspond to values in the template file. For example, if the first variable is named "AT", the values that follow below it would be used to replace the following code in am input deck (template file)

	*                srch         press          temp         squal
	1000201           0.0    1.013529e5          {AT}           0.0

...would become, based on the value for Scenario 501 in the sample "input deck" above (note how it affects the spacing of the following `0.0`):

	*                srch         press          temp         squal
	1000201           0.0    1.013529e5          247.87           0.0

Variable names with a period (.) in the header name are used as a multiplier in the template file. The value to multiply is based on whitespace following its listing in the template file. For example, for the first multiplier variable ".PVth" in the example input deck for a template file:

	*                 temp        thcond
	20100301         250.0        {PVth}13.25
	20100302         300.0        {PVth}13.25
	20100303        1671.0        {PVth}39.162
	20100304        1727.0        {PVth}20.0
	20100305        3000.0        {PVth}20.0

...would become, based on the value for Scenario 501 from the sample "input deck" above:

	*                 temp        thcond
	20100301         250.0        10.6109975
	20100302         300.0        10.6109975
	20100303        1671.0        31.36210446
	20100304        1727.0        16.0166
	20100305        3000.0        16.0166

A new feature... `4$.VAR$5` with a value X below the input will mean `{VAR}{N}` becomes `    (N*X)     ` where (N*X) is a format `:.4E`, where `1234` would become `1.2340e3` and `1230498102348` would become `1.2305e12`.   This is currently hard-coded in that format in `APPROD_Threads.py` but we can propose a change later perhaps.

So the main idea is the integer before the first "$" is the number of spaces before, the integer after the second "$" is the number of spaces after, the period is still required, and the value N is now encased in its own "{}" rather than being white-space delimited.


<h2>Summary</h2>
The APPROD software runs in a distributed mode.
The "server" client should be invoked once. On this computer it will be the head node.
The "client" clients should be invoked on the machines that will do the calculations.
Typical operation consists of invoking the command "screen", followed by navigating to the APPROD directory and invoking  "python27 APPROD.py"

