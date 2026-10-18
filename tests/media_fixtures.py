from pathlib import Path
import subprocess


def make_pdf(directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    source=directory/'aws-demo.ps';target=directory/'aws-demo.pdf'
    source.write_text('''%!PS-Adobe-3.0
<< /PageSize [612 792] >> setpagedevice
/Helvetica-Bold findfont 24 scalefont setfont
60 730 moveto (AWS: Identity and permissions) show
/Helvetica findfont 14 scalefont setfont
60 680 moveto (IAM manages identities and their access to AWS resources.) show
60 650 moveto (A policy states which actions are allowed on a resource.) show
60 620 moveto (Least privilege grants only permissions required by a task.) show
showpage
/Helvetica-Bold findfont 24 scalefont setfont
60 730 moveto (Figure 1: Permission flow) show
0.20 0.45 0.80 setrgbcolor 40 440 150 110 rectfill
0.65 0.35 0.85 setrgbcolor 230 440 150 110 rectfill
0.90 0.50 0.15 setrgbcolor 420 440 150 110 rectfill
1 1 1 setrgbcolor /Helvetica-Bold findfont 20 scalefont setfont
73 490 moveto (Identity) show
270 490 moveto (Policy) show
453 490 moveto (S3 bucket) show
0 0 0 setrgbcolor 3 setlinewidth
190 495 moveto 225 495 lineto stroke
215 502 moveto 225 495 lineto 215 488 lineto stroke
380 495 moveto 415 495 lineto stroke
405 502 moveto 415 495 lineto 405 488 lineto stroke
/Helvetica findfont 14 scalefont setfont
55 375 moveto (An identity uses a policy to authorize access to an S3 bucket.) show
55 345 moveto (The diagram separates identity, permissions and resource.) show
showpage
''')
    subprocess.run(['ps2pdf',str(source),str(target)],check=True)
    return target
