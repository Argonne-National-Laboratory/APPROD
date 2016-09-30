# APPROD
APPROD: An App to Prod Values in Deterministic Models

The software takes any deterministic simulation code (non-specific) and modifies identified variables in the input-deck for the simulation code before launching a "run" of the code. This process is repeated N times and is useful for Probabilistic Risk Assessment studies as well as any other study requiring many parametric changes to variables in a deterministic code.

This program (the Server) will launch RELAP5-3D permutations based on a defined APPROD input file. The Server program was designed with the goal of being code-agnostic, and as such can be developed further to link with other simulation codes. This is accomplished through running a generic batch or shell file (depending on the platform), where the batch or shell file will specify how to launch the simulation code and any post-processing that should be performed.

After each successful individual run, APPROD can copy the results of the run and any post-processed work to a central location. In this sense it also acts as a "job-manager" which can distribute the jobs across many machines. This is useful for non-parallelized code where single-thread speed is important, such that you could group several desktops together into one distributed system.
