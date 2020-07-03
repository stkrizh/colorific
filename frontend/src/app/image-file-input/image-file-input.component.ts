import { Component, OnInit, HostListener, forwardRef, ElementRef } from '@angular/core';
import { NG_VALUE_ACCESSOR } from '@angular/forms';

@Component({
  selector: 'image-file-input',
  templateUrl: './image-file-input.component.html',
  styleUrls: ['./image-file-input.component.scss'],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => ImageFileInputComponent),
      multi: true
    }
  ]
})
export class ImageFileInputComponent implements OnInit {

  public file: File | null = null;
  public onChange: Function;
  public onTouched: Function;

  constructor(private host: ElementRef<HTMLInputElement>) {
    // ---
  }

  ngOnInit() {
    // ---
  }

  @HostListener('change', ['$event.target.files'])
  emitFiles(event: FileList) {
    const file = event && event.item(0);
    this.file = file;
    this.onChange(file);
    this.onTouched();
  }

  writeValue(value: null) {
    // clear file input
    this.host.nativeElement.value = '';
    this.file = null;
  }

  registerOnChange(fn: Function) {
    this.onChange = fn;
  }

  registerOnTouched(fn: Function) {
    this.onTouched = fn;
  }

}
