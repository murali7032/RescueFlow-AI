import fs from 'node:fs/promises';
import { FileBlob, PresentationFile } from '@oai/artifact-tool';

const source = 'C:/Users/MKREDDY/Downloads/Submission Template _ AI Builder Cup.pptx';
const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
console.log('slides', presentation.slides.items.length);
const inspected = await presentation.inspect({
  select: '$.slides[*]',
  include: [
    'id', 'index', 'layout', 'title', 'elements.id', 'elements.kind',
    'elements.text', 'elements.alt', 'notes.text',
  ],
});
await fs.writeFile('.pptx-work/inspection.ndjson', inspected.ndjson, 'utf8');
for (const [index, slide] of presentation.slides.items.entries()) {
  const png = await presentation.export({ slide, format: 'png', scale: 1 });
  await fs.writeFile(`.pptx-work/slide-${String(index + 1).padStart(2, '0')}.png`, new Uint8Array(await png.arrayBuffer()));
}
const montage = await presentation.export({ format: 'webp', montage: true, scale: 1 });
await fs.writeFile('.pptx-work/montage.webp', new Uint8Array(await montage.arrayBuffer()));
