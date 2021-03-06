"""
Example generation for the scikit learn

Generate the rst files for the examples by iterating over the python
example files.

Files that generate images should start with 'plot'

"""
import os
import sys
import shutil
import traceback
import glob
from time import time
from StringIO import StringIO

import matplotlib
matplotlib.use('Agg')

import token, tokenize

###############################################################################
# A tee object to redict streams to multiple outputs

class Tee(object):

    def __init__(self, file1, file2):
        self.file1 = file1
        self.file2 = file2

    def write(self, data):
        self.file1.write(data)
        self.file2.write(data)

    def flush(self):
        self.file1.flush()
        self.file2.flush()



rst_template = """

.. _example_%(short_fname)s:

%(docstring)s

**Python source code:** :download:`%(fname)s <%(fname)s>`

.. literalinclude:: %(fname)s
    :lines: %(end_row)s-
    """

plot_rst_template = """

.. _example_%(short_fname)s:

%(docstring)s

**Python source code:** :download:`%(fname)s <%(fname)s>`

.. literalinclude:: %(fname)s
    :lines: %(end_row)s-

%(image_list)s

%(stdout)s

**Total running time of the example:** %(time_elapsed) .2f seconds
    """

# The following strings are used when we have several pictures: we use
# an html div tag that our CSS uses to turn the lists into horizontal
# lists.
HLIST_HEADER = """
.. rst-class:: horizontal

"""

HLIST_IMAGE_TEMPLATE = """
    *

      .. image:: images/%s
            :scale: 50
"""

SINGLE_IMAGE = """
.. image:: images/%s
    :align: center
"""

def extract_docstring(filename):
    """ Extract a module-level docstring, if any
    """
    lines = file(filename).readlines()
    start_row = 0
    if lines[0].startswith('#!'):
        lines.pop(0)
        start_row = 1

    docstring = ''
    first_par = ''
    tokens = tokenize.generate_tokens(lines.__iter__().next)
    for tok_type, tok_content, _, (erow, _), _ in tokens:
        tok_type = token.tok_name[tok_type]
        if tok_type in ('NEWLINE', 'COMMENT', 'NL', 'INDENT', 'DEDENT'):
            continue
        elif tok_type == 'STRING':
            docstring = eval(tok_content)
            # If the docstring is formatted with several paragraphs, extract
            # the first one:
            paragraphs = '\n'.join(line.rstrip()
                                for line in docstring.split('\n')).split('\n\n')
            if len(paragraphs) > 0:
                first_par = paragraphs[0]
        break
    return docstring, first_par, erow+1+start_row


def generate_all_example_rst(app):
    """ Generate the list of examples, as well as the contents of
        examples.
    """
    input_dir = os.path.abspath(app.builder.srcdir)
    try:
        plot_gallery = eval(app.builder.config.plot_gallery)
    except TypeError:
        plot_gallery = bool(app.builder.config.plot_gallery)
    # Walk all our source tree to find examples and generate them
    for dir_path, dir_names, file_names in os.walk(input_dir):
        if ('build' in dir_path.split(os.sep)
                    or 'auto_examples' in dir_path.split(os.sep)):
            continue
        if 'examples' in dir_names:
            generate_example_rst(
                            os.path.join(dir_path, 'examples'),
                            os.path.join(dir_path, 'auto_examples'),
                            plot_gallery=plot_gallery)


def generate_example_rst(example_dir, out_dir, plot_gallery=False):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    # we create an index.rst with all examples
    fhindex = file(os.path.join(out_dir, 'index.rst'), 'w')
    fhindex.write("""\

.. raw:: html

    <style type="text/css">
    .figure {
        float: left;
        margin: 10px;
        width: auto;
        height: 200px;
        width: 180px;
    }

    .figure img {
        display: inline;
        }

    .figure .caption {
        width: 170px;
        text-align: center !important;
    }
    </style>

Examples
========

.. _examples-index:
""")
    generate_dir_rst('.', fhindex, example_dir, out_dir, plot_gallery)
    fhindex.flush()


def generate_dir_rst(dir, fhindex, example_dir, out_dir, plot_gallery):
    """ Generate the rst file for an example directory.
    """
    if not dir == '.':
        target_dir = os.path.join(out_dir, dir)
        src_dir = os.path.join(example_dir, dir)
    else:
        target_dir = out_dir
        src_dir = example_dir

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    for fname in sorted(os.listdir(src_dir)):
        if fname.endswith('.py'):
            generate_file_rst(fname, target_dir, src_dir, plot_gallery)
            thumb = os.path.join(dir, 'images', 'thumb', fname[:-3] + '.png')
            link_name = os.path.join(dir, fname).replace(os.path.sep, '_')
            fhindex.write('.. figure:: %s\n' % thumb)
            if link_name.startswith('._'):
                link_name = link_name[2:]
            if dir != '.':
                fhindex.write('   :target: ./%s/%s.html\n\n' % (dir, fname[:-3]))
            else:
                fhindex.write('   :target: ./%s.html\n\n' % link_name[:-3])
            fhindex.write('   :ref:`example_%s`\n\n' % link_name)
    fhindex.write("""
.. raw:: html

    <div style="clear: both"></div>
    """) # clear at the end of the section


def generate_file_rst(fname, target_dir, src_dir, plot_gallery):
    """ Generate the rst file for a given example.
    """
    base_image_name = os.path.splitext(fname)[0]
    image_fname = '%s_%%s.png' % base_image_name

    this_template = rst_template
    last_dir = os.path.split(src_dir)[-1]
    # to avoid leading . in file names, and wrong names in links
    if last_dir == '.' or last_dir == 'examples':
        last_dir = ''
    else:
        last_dir += '_'
    short_fname = last_dir + fname
    src_file = os.path.join(src_dir, fname)
    example_file = os.path.join(target_dir, fname)
    shutil.copyfile(src_file, example_file)

    # The following is a list containing all the figure names
    figure_list = []

    image_dir = os.path.join(target_dir, 'images')
    thumb_dir = os.path.join(image_dir, 'thumb')
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)
    if not os.path.exists(thumb_dir):
        os.makedirs(thumb_dir)
    image_path = os.path.join(image_dir, image_fname)
    stdout_path = os.path.join(image_dir,
                               'stdout_%s.txt' % base_image_name)
    time_path = os.path.join(image_dir,
                               'time_%s.txt' % base_image_name)
    thumb_file = os.path.join(thumb_dir, fname[:-3] + '.png')
    time_elapsed = 0
    if plot_gallery and fname.startswith('plot'):
        # generate the plot as png image if file name
        # starts with plot and if it is more recent than an
        # existing image.
        first_image_file = image_path % 1
        if os.path.exists(stdout_path):
            stdout = open(stdout_path).read()
        else:
            stdout = ''
        if os.path.exists(time_path):
            time_elapsed = float(open(time_path).read())

        if (not os.path.exists(first_image_file) or
                os.stat(first_image_file).st_mtime <=
                                    os.stat(src_file).st_mtime):
            # We need to execute the code
            print 'plotting %s' % fname
            t0 = time()
            import matplotlib.pyplot as plt
            plt.close('all')
            cwd = os.getcwd()
            try:
                # First CD in the original example dir, so that any file
                # created by the example get created in this directory
                orig_stdout = sys.stdout
                os.chdir(os.path.dirname(src_file))
                my_buffer = StringIO()
                my_stdout = Tee(sys.stdout, my_buffer)
                sys.stdout = my_stdout
                my_globals = {'pl': plt}
                execfile(os.path.basename(src_file), my_globals)
                time_elapsed = time() - t0
                sys.stdout = orig_stdout
                my_stdout = my_buffer.getvalue()

                os.chdir(cwd)

                # In order to save every figure we have two solutions :
                # * iterate from 1 to infinity and call plt.fignum_exists(n)
                #   (this requires the figures to be numbered
                #    incrementally: 1, 2, 3 and not 1, 2, 5)
                # * iterate over [fig_mngr.num for fig_mngr in
                #   matplotlib._pylab_helpers.Gcf.get_all_fig_managers()]
                for fig_num in (fig_mngr.num for fig_mngr in
                          matplotlib._pylab_helpers.Gcf.get_all_fig_managers()):
                    # Set the fig_num figure as the current figure as we can't
                    # save a figure that's not the current figure.
                    plt.figure(fig_num)
                my_stdout = my_stdout.strip()
                if my_stdout:
                    stdout = '**Script output**::\n\n  %s\n\n' % (
                        '\n  '.join(my_stdout.split('\n')))
                open(stdout_path, 'w').write(stdout)
                open(time_path, 'w').write('%f' % time_elapsed)
                my_stdout = my_stdout.strip()
                if my_stdout:
                    stdout = '**Script output**::\n\n  %s\n\n' % (
                        '\n  '.join(my_stdout.split('\n')))
                open(stdout_path, 'w').write(stdout)
                open(time_path, 'w').write('%f' % time_elapsed)
                plt.savefig(image_path % fig_num)
                figure_list.append(image_fname % fig_num)
            except:
                print 80*'_'
                print '%s is not compiling:' % fname
                traceback.print_exc()
                print 80*'_'
            finally:
                os.chdir(cwd)
        else:
            figure_list = [f[len(image_dir):]
                            for f in glob.glob(image_path % '[1-9]')]
                            #for f in glob.glob(image_path % '*')]

        # generate thumb file
        this_template = plot_rst_template
        from matplotlib import image
        if os.path.exists(first_image_file):
            image.thumbnail(first_image_file, thumb_file, 0.2)

    if not os.path.exists(thumb_file):
        # create something not to replace the thumbnail
        shutil.copy('blank_image.png', thumb_file)

    docstring, short_desc, end_row = extract_docstring(example_file)

    # Depending on whether we have one or more figures, we're using a
    # horizontal list or a single rst call to 'image'.
    if len(figure_list) == 1:
        figure_name = figure_list[0]
        image_list = SINGLE_IMAGE % figure_name.lstrip('/')
    else:
        image_list = HLIST_HEADER
        for figure_name in figure_list:
            image_list += HLIST_IMAGE_TEMPLATE % figure_name.lstrip('/')

    f = open(os.path.join(target_dir, fname[:-2] + 'rst'),'w')
    f.write(this_template % locals())
    f.flush()


def setup(app):
    app.connect('builder-inited', generate_all_example_rst)
    app.add_config_value('plot_gallery', True, 'html')
