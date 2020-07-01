import { Component, OnInit, OnDestroy } from "@angular/core";
import { DomSanitizer, SafeStyle } from "@angular/platform-browser";
import { AbstractControl, FormGroup, FormControl, Validators, ValidatorFn } from '@angular/forms';
import { HttpClient } from "@angular/common/http";
import { Subscription } from 'rxjs';
import { Color, ColorsResponse } from "../types";
import { FileSizePipe } from 'ngx-filesize';


const MAX_IMAGE_FILE_SIZE_MB = 5;


@Component({
  selector: "app-image-loader",
  templateUrl: "./image-loader.component.html",
  styleUrls: ["./image-loader.component.scss"]
})
export class ImageLoaderComponent implements OnInit, OnDestroy {

  public colorsResponse: ColorsResponse | null = null;
  public form = new FormGroup({
    imageFile: new FormControl(
      '',
      Validators.compose([
        fileTypeValidator(['image/jpeg', 'image/png', 'image/gif']),
        fileSizeValidator(MAX_IMAGE_FILE_SIZE_MB)
      ])
    ),
    imageURL: new FormControl(
      '',
      Validators.compose([
        Validators.pattern(/(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})/)
      ])
    )
  }, {
    validators: imageProvidedValidator,
    updateOn: 'change'
  });
  public imageLoadErrorMessage: string | null = null;
  public imagePreviewURL: string | null = null;
  public isImageLoading: boolean = false;
  public rgb: string | null = null;

  private formStatusObserver: Subscription;
  private imageFileObserver: Subscription;
  private imageURLObserver: Subscription;

  constructor(
    private http: HttpClient,
    private sanitizer: DomSanitizer,
  ) {}

  ngOnInit() {
    this.imageFileObserver = this.imageFile.valueChanges.subscribe((value) => {
      this.imageURL.reset('', {emitEvent: false});
    });
    this.imageURLObserver = this.imageURL.valueChanges.subscribe((value) => {
      this.imageFile.reset('', {emitEvent: false});
      if (value === '') this.imageURL.reset('', {emitEvent: false});
    })

    this.formStatusObserver = this.form.statusChanges.subscribe(status => {
      this.resetForm();

      if (status == 'INVALID') {
        this.imagePreviewURL = null;
        return;
      }

      if (this.imageURL.value) {
        this.imagePreviewURL = this.imageURL.value;
        return;
      }

      const reader = new FileReader();
      reader.readAsDataURL(this.imageFile.value);
      reader.onload = () => this.imagePreviewURL = <string>reader.result;
      reader.onerror = () => this.imagePreviewURL = null;
      reader.onabort = () => this.imagePreviewURL = null;
      return;
    })
  }

  ngOnDestroy() {
    this.formStatusObserver.unsubscribe();
    this.imageFileObserver.unsubscribe();
    this.imageURLObserver.unsubscribe();
  }

  get imageFile(): AbstractControl {
    return this.form.controls['imageFile'];
  }

  get imageURL(): AbstractControl {
    return this.form.controls['imageURL'];
  }

  get isImageSelected(): boolean {
    return this.form.dirty && this.form.valid;
  }

  get formError(): string {
    if (this.imageFile.errors) {
      if (this.imageFile.errors.invalidFileType) {
        return 'Допускаются только JPEG, PNG или GIF изображения';
      }
      if (this.imageFile.errors.fileTooLarge) {
        let pipe = new FileSizePipe();
        let actualSize = pipe.transform(this.imageFile.errors.fileTooLarge['value']);
        return (
          `Максимальный размер изображения ${MAX_IMAGE_FILE_SIZE_MB} Mb. `
          + `Сейчас ${actualSize}`
        )
      }
      throw new Error('Unexpected error with `imageFile` control');
    }
    if (this.imageURL.errors) {
      if (this.imageURL.errors.pattern) {
        return 'Укажите корректный URL изображения';
      }
      throw new Error('Unexpected error with `imageURL` control');
    }
    return '';
  }

  get imagePreviewBackgroundURL(): SafeStyle | null {
    if (this.imagePreviewURL === null) return null;
    return this.sanitizer.bypassSecurityTrustStyle(
      `url(${this.imagePreviewURL})`
    );
  }

  resetForm() {
    this.colorsResponse = null;
    this.imageLoadErrorMessage = null;
    this.rgb = null;
  }

  submitForm() {
    this.isImageLoading = true;
    let body;
  
    if (this.imageFile.value)
      body = this.imageFile.value;
    else
      body = {url: this.imageURL.value};

    this.http.put("http://0.0.0.0:8080/image", body).subscribe(
      response => {
        this.isImageLoading = false;
        this.colorsResponse = new ColorsResponse(<Color[]>response);
      },
      error => {
        this.isImageLoading = false;
        if (error.status == 400) {
          if ('image' in error.error)
            this.imageLoadErrorMessage = error.error.image[0];
          else if ('url' in error.error)
            this.imageLoadErrorMessage = error.error.url;
          else {
            this.imageLoadErrorMessage = 'Произошла ошибка. Попробуйте выбрать другое изображение.'
          }
        } else {
          this.imageLoadErrorMessage = (
            'Произошла ошибка. Попробуйте повторить позднее.'
          )
        }
      }
    );
  }

  showImageList(color: Color) {
    this.rgb = color.toHex();
  }
}


function imageProvidedValidator(control: FormGroup): {[key: string]: any} | null {
  const imageFile = control.get('imageFile');
  const imageURL = control.get('imageURL');

  return imageFile && imageURL && (imageFile.value || imageURL.value) ? null : {
    'imageNotProvided': true
  };
};


function fileTypeValidator(allowedTypes: string[]): ValidatorFn {
  return (control: AbstractControl): {[key: string]: any} | null => {
    if (!control.value) return null;
    if (!('type' in control.value)) return null;
    return allowedTypes.includes(control.value.type) ? null : {
      'invalidFileType': {value: control.value.type}
    }
  };
}


function fileSizeValidator(allowedSize: number): ValidatorFn {
  return (control: AbstractControl): {[key: string]: any} | null => {
    if (!(control.value)) return null;
    if (!('size' in control.value)) return null;
    return control.value.size <= (allowedSize * 2**20) ? null : {
      'fileTooLarge': {value: control.value.size}
    }
  };
}
