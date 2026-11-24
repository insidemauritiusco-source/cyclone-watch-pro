from PIL import Image
from tv_layout import render_card,ass_captions
from pathlib import Path
from tempfile import TemporaryDirectory
p={'lat':-9.5,'lon':77.1,'observed':'24 November 2026 04 AM'}
d=dict(name='TEST — NOT AN OFFICIAL BULLETIN',obs='Test observation',fresh=False,pressure='—',speed='—',distance='—',direction='—',coord='—',warning='Non vérifié',checked='Test',track=[p],bearing='south')
for lang in ('fr','mfe'):
 for frame in (None,Image.new('RGB',(800,600),'#23556f')):
  for poster in (False,True):
   card=render_card(lang,d,frame,'Test UTC',1,0,poster=poster)
   assert card.size==(2160,3840)
with TemporaryDirectory() as t:
 for landscape in (False,True):
  p=Path(t)/'captions.ass';ass_captions([(0,2,'Test de sous-titres pour vérifier la mise en page.')],p,landscape)
  assert 'Dialogue:' in p.read_text()
print('PASS V24 layout smoke test: portrait image, no-image fallback, poster and caption generation')