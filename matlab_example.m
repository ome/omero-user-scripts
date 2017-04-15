function main
% Example MATLAB script which can be dropped into
% dist/lib/scripts in order to test multiple script
% types.

% Copyright (C) 2013 University of Dundee & Open Microscopy Environment.
% All rights reserved.
%
% This program is free software; you can redistribute it and/or modify
% it under the terms of the GNU General Public License as published by
% the Free Software Foundation; either version 2 of the License, or
% (at your option) any later version.
%
% This program is distributed in the hope that it will be useful,
% but WITHOUT ANY WARRANTY; without even the implied warranty of
% MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
% GNU General Public License for more details.
%
% You should have received a copy of the GNU General Public License along
% with this program; if not, write to the Free Software Foundation, Inc.,
% 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

[c, s] = loadOmero();
cleanup = onCleanup(@unloadOmero);

parse = c.getProperty('omero.scripts.parse');
if parse.isEmpty()
    % Perform job
    % =========================================
    fprintf(1, 'Found in1: %s\n', c.getInput('in1'));
    fprintf(1, 'Setting out1 to 0...');
    c.setOutput('out1', rint(0));
else
    % Parsing. See OmeroPy/src/omero/scripts.py
    % for the Python implementation.
    % =========================================
    c.setOutput('omero.scripts.parse', getParams());
    % throw(MException('Parsing'));  % Return code ignored.
    error('Parsing');  % Return code ignored.
end

function params = getParams
% Generate a params object with dummy data
in1 = omero.grid.Param();
in1.optional = false;
in1.prototype = omero.rtypes.rint(0);
in1.description = 'Some arbitrary integer';

out1 = omero.grid.Param();
out1.optional = true;
out1.prototype = omero.rtypes.rint(0);
out1.description = 'Always 0';

params = omero.grid.JobParams();
params.name = 'matlab_example.m';
params.version = '0.0.1';
params.description = 'An example MATLAB script';
params.inputs = java.util.HashMap;
params.inputs.put('in1', in1);
params.outputs = java.util.HashMap;
params.outputs.put('out1', out1);
params.stdoutFormat = 'text/plain';
params.stderrFormat = 'text/plain';

params = omero.rtypes.rinternal(params);
